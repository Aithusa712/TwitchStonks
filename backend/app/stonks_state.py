import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import WebSocket
from motor.motor_asyncio import AsyncIOMotorCollection

logger = logging.getLogger(__name__)


@dataclass
class PricePoint:
    timestamp: datetime
    price: float
    up_count: int
    down_count: int

    def to_db(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "price": self.price,
            "up_count": self.up_count,
            "down_count": self.down_count,
        }

    def to_json(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            "price": self.price,
            "up_count": self.up_count,
            "down_count": self.down_count,
        }


class StonksState:
    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        up_keyword: str,
        down_keyword: str,
        tick_interval_minutes: float = 30.0,
        initial_price: float = 100.0,
    ):
        self.collection = collection
        self.up_keyword = up_keyword.lower()
        self.down_keyword = down_keyword.lower()
        self.tick_interval_minutes = tick_interval_minutes
        self.tick_interval_seconds = tick_interval_minutes * 60
        self.current_price = initial_price
        self._up_counter = 0
        self._down_counter = 0
        self._ticker_task: asyncio.Task | None = None
        self._running = False
        self._websockets: List[WebSocket] = []
        self.next_tick_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.tick_interval_seconds
        )
        self.twitch_connected = False
        self.stream_live = False

    def increment_up(self) -> None:
        self._up_counter += 1
        logger.debug("Incremented UP counter: %s", self._up_counter)

    def increment_down(self) -> None:
        self._down_counter += 1
        logger.debug("Incremented DOWN counter: %s", self._down_counter)

    def handle_message(self, message: str) -> None:
        lowered = message.lower()
        matched = False
        if self.up_keyword in lowered:
            self.increment_up()
            matched = True
        if self.down_keyword in lowered:
            self.increment_down()
            matched = True
        if matched:
            logger.info(
                "Received twitch message affecting counters (up=%s, down=%s)",
                self._up_counter,
                self._down_counter,
            )

    async def start(self) -> None:
        if self._running:
            return
        latest = await self.collection.find_one(sort=[("timestamp", -1)])
        if latest and "price" in latest:
            try:
                self.current_price = float(latest["price"])
                logger.info(
                    "Starting with previous price from database: %.2f",
                    self.current_price,
                )
            except (TypeError, ValueError):
                logger.warning(
                    "Previous price found in database but invalid, using initial price: %.2f",
                    self.current_price,
                )
        else:
            logger.info(
                "No previous price found in database, using initial price: %.2f",
                self.current_price,
            )
        self._running = True
        logger.info("Starting ticker loop with interval %.2f minutes", self.tick_interval_minutes)
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
            await asyncio.sleep(self.tick_interval_seconds)
            try:
                await self._tick()
            except Exception as exc:  # pragma: no cover - safety net
                logger.error("Ticker execution failed: %s", exc)

    async def _tick(self) -> None:
        up_count = self._up_counter
        down_count = self._down_counter
        self._up_counter = 0
        self._down_counter = 0
        if up_count == 0 and down_count == 0:
            self.next_tick_at = datetime.now(timezone.utc) + timedelta(
                seconds=self.tick_interval_seconds
            )
            logger.info("Ticker skipped due to no activity (up=0, down=0)")
            return
        price_change = (up_count * 0.5) - (down_count * 0.5)
        self.current_price = max(0.0, self.current_price + price_change)
        point = PricePoint(
            timestamp=datetime.now(timezone.utc),
            price=self.current_price,
            up_count=up_count,
            down_count=down_count,
        )
        self.next_tick_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.tick_interval_seconds
        )
        await self.collection.insert_one(point.to_db())
        logger.info(
            "Ticker executed: price=%.2f, up_count=%s, down_count=%s",
            self.current_price,
            up_count,
            down_count,
        )
        await self._broadcast(point)

    async def _broadcast(self, point: PricePoint) -> None:
        payload = {
            **point.to_json(),
            "next_tick_at": self.next_tick_at.isoformat(),
            "twitch_connected": self.twitch_connected,
            "stream_live": self.stream_live,
            "type": "tick",
        }
        await self._send_payload(payload)

    async def _broadcast_status_update(self) -> None:
        payload = {
            "type": "status",
            "twitch_connected": self.twitch_connected,
            "stream_live": self.stream_live,
            "next_tick_at": self.next_tick_at.isoformat(),
        }
        await self._send_payload(payload)

    async def _send_payload(self, payload: Dict[str, object]) -> None:
        message = json.dumps(payload)
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
            latest_ts = latest.get("timestamp")
            if isinstance(latest_ts, str):
                ts_value = datetime.fromisoformat(latest_ts)
            elif latest_ts is None:
                ts_value = datetime.now(timezone.utc)
            else:
                ts_value = latest_ts
            if ts_value.tzinfo is None:
                ts_value = ts_value.replace(tzinfo=timezone.utc)
            latest_payload = {
                "timestamp": ts_value.isoformat(),
                "price": latest.get("price", 0.0),
                "up_count": latest.get("up_count", 0),
                "down_count": latest.get("down_count", 0),
                "next_tick_at": self.next_tick_at.isoformat(),
                "twitch_connected": self.twitch_connected,
                "stream_live": self.stream_live,
            }
            await websocket.send_text(json.dumps(latest_payload))

    def keyword_in_message(self, message: str) -> bool:
        lowered = message.lower()
        return self.up_keyword in lowered or self.down_keyword in lowered

    def set_twitch_status(self, connected: bool) -> None:
        if self.twitch_connected == connected:
            return
        self.twitch_connected = connected
        logger.info("Twitch connection status changed: %s", connected)
        asyncio.create_task(self._broadcast_status_update())

    def set_stream_status(self, is_live: bool) -> None:
        if self.stream_live == is_live:
            return
        self.stream_live = is_live
        logger.info("Twitch stream live status changed: %s", is_live)
        asyncio.create_task(self._broadcast_status_update())
