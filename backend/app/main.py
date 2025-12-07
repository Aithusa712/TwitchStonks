import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorCollection

from .config import settings
from .db import close_client, ensure_database_connection, get_database
from .stonks_state import StonksState
from .twitch_client import TwitchClient
from .twitch_helix_client import TwitchHelixClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("twitch_stonks")

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://localhost:5173",
    "http://127.0.0.1:5173",
    "https://gray-plant-0d92e610f.3.azurestaticapps.net",
    "https://www.stonkstracker.live",
]
AZURE_STATIC_ORIGIN_REGEX = r"https://.*\\.azurestaticapps\\.net"

app = FastAPI(title="Twitch Stonks")
allowed_origins = DEFAULT_ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=AZURE_STATIC_ORIGIN_REGEX,
)
logger.info("Configured CORS for origins: %s", allowed_origins)


RANGE_MAP = {
    "today": timedelta(days=1),
    "3days": timedelta(days=3),
    "7days": timedelta(days=7),
    "30days": timedelta(days=30),
    "3months": timedelta(days=90),
    "6months": timedelta(days=180),
    "1year": timedelta(days=365),
}


AGGREGATE_HOURLY_MAX_DAYS = 7


def get_collection() -> AsyncIOMotorCollection:
    db = get_database(settings.mongo_uri, settings.mongo_db_name)
    return db["price_ticks"]


@app.on_event("startup")
async def startup_event() -> None:
    await ensure_database_connection(settings.mongo_uri)
    collection = get_collection()
    state = StonksState(
        collection=collection,
        up_keyword=settings.stonks_up_keyword,
        down_keyword=settings.stonks_down_keyword,
        tick_interval_minutes=settings.tick_interval_minutes,
        initial_price=settings.initial_price,
    )
    twitch = TwitchClient(
        username=settings.twitch_bot_username,
        oauth_token=settings.twitch_oauth_token,
        channel=settings.twitch_channel,
        on_message=lambda msg: state.handle_message(msg)
        if state.keyword_in_message(msg)
        else None,
        on_status_change=state.set_twitch_status,
    )
    helix = TwitchHelixClient(
        client_id=settings.twitch_client_id,
        client_secret=settings.twitch_client_secret,
        channel=settings.twitch_channel,
        on_status_change=state.set_stream_status,
        poll_interval_seconds=180,
    )
    await state.start()
    try:
        await twitch.start()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to start Twitch client: %s", exc)
    try:
        await helix.start()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to start Twitch Helix client: %s", exc)
    app.state.stonks_state = state
    app.state.twitch_client = twitch
    app.state.twitch_helix_client = helix


@app.on_event("shutdown")
async def shutdown_event() -> None:
    state: StonksState = app.state.stonks_state
    twitch: TwitchClient = app.state.twitch_client
    helix: TwitchHelixClient = app.state.twitch_helix_client
    await helix.stop()
    await twitch.stop()
    await state.stop()
    close_client()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
async def status() -> dict[str, Any]:
    state: StonksState = app.state.stonks_state
    twitch: TwitchClient = app.state.twitch_client
    return {
        "twitch_connected": twitch.connected,
        "stream_live": state.stream_live,
        "next_tick_at": state.next_tick_at.isoformat(),
        "current_price": state.current_price,
        "tick_interval_minutes": state.tick_interval_minutes,
        "twitch_channel": settings.twitch_channel,
        "up_keyword": settings.stonks_up_keyword,
        "down_keyword": settings.stonks_down_keyword,
    }


@app.get("/history")
async def history(
    range: str = "today",
    collection: AsyncIOMotorCollection = Depends(get_collection),
) -> List[dict[str, Any]]:
    if range not in RANGE_MAP:
        raise HTTPException(status_code=400, detail="Invalid range")
    start_time = datetime.now(timezone.utc) - RANGE_MAP[range]
    unit = "hour" if RANGE_MAP[range].days <= AGGREGATE_HOURLY_MAX_DAYS else "day"
    base_pipeline = [
        {"$match": {"timestamp": {"$lt": start_time}}},
        {
            "$group": {
                "_id": None,
                "total_up": {"$sum": {"$ifNull": ["$up_count", 0]}},
                "total_down": {"$sum": {"$ifNull": ["$down_count", 0]}},
            }
        },
    ]
    base_cursor = collection.aggregate(base_pipeline)
    base_totals = await base_cursor.to_list(length=1)
    base_up = base_totals[0].get("total_up", 0) if base_totals else 0
    base_down = base_totals[0].get("total_down", 0) if base_totals else 0
    base_price = max(0.0, settings.initial_price + ((base_up - base_down) * 0.5))

    counts_by_bucket: dict[datetime, dict[str, int]] = {}

    def normalize_timestamp(raw_ts: Any) -> datetime:
        if isinstance(raw_ts, str):
            ts_value = datetime.fromisoformat(raw_ts)
        elif raw_ts is None:
            ts_value = datetime.now(timezone.utc)
        else:
            ts_value = raw_ts
        if ts_value.tzinfo is None:
            ts_value = ts_value.replace(tzinfo=timezone.utc)
        return ts_value.astimezone(timezone.utc)

    def truncate_timestamp(ts_value: datetime) -> datetime:
        if unit == "hour":
            return ts_value.replace(minute=0, second=0, microsecond=0)
        return ts_value.replace(hour=0, minute=0, second=0, microsecond=0)

    cursor = collection.find({"timestamp": {"$gte": start_time}}).sort("timestamp", 1)
    async for doc in cursor:
        ts_value = normalize_timestamp(doc.get("timestamp"))
        bucket = truncate_timestamp(ts_value)
        counts = counts_by_bucket.setdefault(bucket, {"up": 0, "down": 0})
        counts["up"] += int(doc.get("up_count", 0) or 0)
        counts["down"] += int(doc.get("down_count", 0) or 0)

    price = base_price
    results: List[dict[str, Any]] = []
    for bucket_ts in sorted(counts_by_bucket.keys()):
        counts = counts_by_bucket[bucket_ts]
        price = max(0.0, price + ((counts["up"] - counts["down"]) * 0.5))
        results.append(
            {
                "timestamp": bucket_ts.replace(tzinfo=timezone.utc).isoformat(),
                "price": price,
                "up_count": counts["up"],
                "down_count": counts["down"],
            }
        )

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
