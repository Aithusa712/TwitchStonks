import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class TwitchHelixClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        channel: str,
        on_status_change: Optional[Callable[[bool], None]] = None,
        poll_interval_seconds: int = 180,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.channel = channel
        self.on_status_change = on_status_change
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._client: httpx.AsyncClient | None = None
        self.last_stream_data: Dict[str, Any] | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=10.0))
        await self._ensure_token()
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._client:
            await self._client.aclose()

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._check_stream_status()
            except Exception as exc:  # pragma: no cover - safety net
                logger.error("Helix poll failed: %s", exc)
            await asyncio.sleep(self.poll_interval_seconds)

    async def _ensure_token(self) -> None:
        if (
            self._token
            and self._token_expires_at
            and self._token_expires_at - datetime.now(timezone.utc) > timedelta(seconds=60)
        ):
            return
        await self._refresh_token()

    async def _refresh_token(self) -> None:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=10.0))
        try:
            response = await self._client.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
            )
            response.raise_for_status()
            payload = response.json()
            self._token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 3600))
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            logger.info("Obtained new Twitch Helix token (expires in %s seconds)", expires_in)
        except Exception as exc:  # pragma: no cover - safety net
            logger.error("Failed to refresh Twitch Helix token: %s", exc)
            self._token = None
            self._token_expires_at = None

    async def _check_stream_status(self) -> None:
        await self._ensure_token()
        if not self._client or not self._token:
            logger.warning("Skipping stream status check: missing token or client")
            return
        headers = {"Authorization": f"Bearer {self._token}", "Client-Id": self.client_id}
        params = {"user_login": self.channel}
        try:
            response = await self._client.get("https://api.twitch.tv/helix/streams", headers=headers, params=params)
            if response.status_code == 401:
                logger.info("Helix token expired, refreshing and retrying")
                await self._refresh_token()
                if not self._token:
                    return
                headers["Authorization"] = f"Bearer {self._token}"
                response = await self._client.get(
                    "https://api.twitch.tv/helix/streams", headers=headers, params=params
                )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", []) if isinstance(payload, dict) else []
            is_live = bool(data)
            self.last_stream_data = data[0] if is_live else None
            self._update_stream_status(is_live)
        except Exception as exc:  # pragma: no cover - safety net
            logger.error("Failed to query Twitch stream status: %s", exc)

    def _update_stream_status(self, is_live: bool) -> None:
        if not self.on_status_change:
            return
        try:
            self.on_status_change(is_live)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Stream status callback failed: %s", exc)

