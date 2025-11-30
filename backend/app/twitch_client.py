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
        on_message: Callable[[str], None],
        use_tls: bool = True,
    ):
        self.username = username
        self.oauth_token = oauth_token
        self.channel = channel
        self.on_message = on_message
        self.use_tls = use_tls
        self._task: Optional[asyncio.Task] = None
        self._running = False

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
                if text is not None:
                    self.on_message(text)

    def _extract_message(self, raw: str) -> Optional[str]:
        try:
            # IRC format: :username!user@host PRIVMSG #channel :message
            _, trailing = raw.split("PRIVMSG", 1)
            if " :" in trailing:
                return trailing.split(" :", 1)[1]
        except ValueError:
            return None
        return None
