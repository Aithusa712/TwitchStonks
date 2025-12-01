from __future__ import annotations

import asyncio
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

client: Optional[AsyncIOMotorClient] = None


def get_client(uri: str) -> AsyncIOMotorClient:
    global client
    if client is None:
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    return client


def get_database(uri: str, db_name: str) -> AsyncIOMotorDatabase:
    mongo_client = get_client(uri)
    return mongo_client[db_name]


def close_client() -> None:
    global client
    if client is not None:
        client.close()
        client = None


async def ensure_database_connection(uri: str, retries: int = 5, delay: float = 1.5) -> AsyncIOMotorClient:
    """Attempt to connect to MongoDB with retries for production stability."""

    last_exception: Exception | None = None
    for attempt in range(1, retries + 1):
        mongo_client = get_client(uri)
        try:
            await mongo_client.admin.command("ping")
            logger.info("MongoDB connection established on attempt %s", attempt)
            return mongo_client
        except Exception as exc:  # pragma: no cover - network dependent
            last_exception = exc
            logger.warning(
                "MongoDB connection attempt %s/%s failed: %s", attempt, retries, exc
            )
            await asyncio.sleep(delay * attempt)

    error_message = "Failed to connect to MongoDB after multiple attempts"
    logger.error(error_message)
    if last_exception:
        raise last_exception
    raise ConnectionError(error_message)
