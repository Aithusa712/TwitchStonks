import logging
from typing import Any, List

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorCollection

from .config import settings
from .db import close_client, get_database
from .stonks_state import StonksState
from .twitch_client import TwitchClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Twitch Stonks")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_collection() -> AsyncIOMotorCollection:
    db = get_database(settings.mongo_uri, settings.mongo_db_name)
    return db["price_ticks"]


@app.on_event("startup")
async def startup_event() -> None:
    collection = get_collection()
    state = StonksState(
        collection=collection,
        keyword=settings.stonks_keyword,
        tick_interval=settings.tick_interval_seconds,
        initial_price=settings.initial_price,
    )
    twitch = TwitchClient(
        username=settings.twitch_bot_username,
        oauth_token=settings.twitch_oauth_token,
        channel=settings.twitch_channel,
        on_message=lambda msg: state.increment()
        if state.keyword_in_message(msg)
        else None,
    )
    await state.start()
    await twitch.start()
    app.state.stonks_state = state
    app.state.twitch_client = twitch


@app.on_event("shutdown")
async def shutdown_event() -> None:
    state: StonksState = app.state.stonks_state
    twitch: TwitchClient = app.state.twitch_client
    await twitch.stop()
    await state.stop()
    close_client()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/history")
async def history(collection: AsyncIOMotorCollection = Depends(get_collection)) -> List[dict[str, Any]]:
    cursor = collection.find().sort("timestamp", 1)
    results: List[dict[str, Any]] = []
    async for doc in cursor:
        doc.pop("_id", None)
        results.append(doc)
    return results


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    state: StonksState = app.state.stonks_state
    await state.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in state._websockets:
            state._websockets.remove(websocket)
    except Exception:
        if websocket in state._websockets:
            state._websockets.remove(websocket)
