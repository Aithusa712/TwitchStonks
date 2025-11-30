import asyncio
import contextlib
import logging
import ssl
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TwitchClient:
    def __init__(
        self,
        username: str,
        oauth_token: str,
        channel: str,
        on_message: Optional[Callable[[str], None]],
        on_status_change: Optional[Callable[[bool], None]] = None,
        use_tls: bool = True,
    ):
        self.username = username
        self.oauth_token = oauth_token
        self.channel = channel
        self.on_message = on_message
        self.on_status_change = on_status_change
        self.use_tls = use_tls
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.connected = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _listen_loop(self) -> None:
        while self._running:
            try:
                await self._connect_and_listen()
            except Exception as exc:
                logger.error("Twitch client error: %s", exc)
                await self._update_status(False)
                await asyncio.sleep(5)

    async def _connect_and_listen(self) -> None:
        ssl_context = ssl.create_default_context() if self.use_tls else None
        reader, writer = await asyncio.open_connection(
            "irc.chat.twitch.tv", 6697 if self.use_tls else 6667, ssl=ssl_context
        )
        writer.write(f"PASS {self.oauth_token}\r\n".encode())
        writer.write(f"NICK {self.username}\r\n".encode())
        writer.write(f"JOIN #{self.channel}\r\n".encode())
        await writer.drain()
        await self._update_status(True)
        logger.info("Connected to Twitch IRC as %s", self.username)

        try:
            while self._running:
                line = await reader.readline()
                if not line:
                    break
                message = line.decode(errors="ignore").strip()
                if message.startswith("PING"):
                    writer.write(message.replace("PING", "PONG").encode() + b"\r\n")
                    await writer.drain()
                    continue
                if "PRIVMSG" in message:
                    text = self._extract_message(message)
                    if text is not None and self.on_message:
                        logger.debug("Twitch message received: %s", text)
                        self.on_message(text)
        finally:
            await self._update_status(False)
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            logger.warning("Twitch IRC connection closed, retrying...")

    def _extract_message(self, raw: str) -> Optional[str]:
        try:
            # IRC format: :username!user@host PRIVMSG #channel :message
            _, trailing = raw.split("PRIVMSG", 1)
            if " :" in trailing:
                return trailing.split(" :", 1)[1]
        except ValueError:
            return None
        return None

    async def _update_status(self, status: bool) -> None:
        if self.connected == status:
            return
        self.connected = status
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception as exc:
                logger.error("Failed to update twitch status callback: %s", exc)
