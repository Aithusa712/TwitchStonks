import asyncio
import contextlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import WebSocket
from motor.motor_asyncio import AsyncIOMotorCollection


@dataclass
class PricePoint:
    timestamp: datetime
    price: float
    count: int

    def to_json(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            "price": self.price,
            "count": self.count,
        }


class StonksState:
    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        keyword: str,
        tick_interval: float = 2.0,
        initial_price: float = 100.0,
    ):
        self.collection = collection
        self.keyword = keyword.lower()
        self.tick_interval = tick_interval
        self.current_price = initial_price
        self._counter = 0
        self._ticker_task: asyncio.Task | None = None
        self._running = False
        self._websockets: List[WebSocket] = []

    def increment(self) -> None:
        self._counter += 1

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._ticker_task = asyncio.create_task(self._ticker_loop())

    async def stop(self) -> None:
        self._running = False
        if self._ticker_task:
            self._ticker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ticker_task
        for ws in list(self._websockets):
            await ws.close()
        self._websockets.clear()

    async def _ticker_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.tick_interval)
            await self._tick()

    async def _tick(self) -> None:
        count = self._counter
        self._counter = 0
        price_change = count * 0.5 - 0.2
        self.current_price = max(0.0, self.current_price + price_change)
        point = PricePoint(
            timestamp=datetime.now(timezone.utc),
            price=self.current_price,
            count=count,
        )
        await self.collection.insert_one(point.to_json())
        await self._broadcast(point)

    async def _broadcast(self, point: PricePoint) -> None:
        message = json.dumps(point.to_json())
        disconnected: List[WebSocket] = []
        for ws in self._websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            if ws in self._websockets:
                self._websockets.remove(ws)

    async def register(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._websockets.append(websocket)
        latest = await self.collection.find_one(sort=[("timestamp", -1)])
        if latest:
            latest.pop("_id", None)
            await websocket.send_text(json.dumps(latest))

    def keyword_in_message(self, message: str) -> bool:
        return self.keyword in message.lower()
