from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

client: Optional[AsyncIOMotorClient] = None


def get_client(uri: str) -> AsyncIOMotorClient:
    global client
    if client is None:
        client = AsyncIOMotorClient(uri)
    return client


def get_database(uri: str, db_name: str) -> AsyncIOMotorDatabase:
    mongo_client = get_client(uri)
    return mongo_client[db_name]


def close_client() -> None:
    global client
    if client is not None:
        client.close()
        client = None
