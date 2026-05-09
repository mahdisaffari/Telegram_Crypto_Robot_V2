from __future__ import annotations

from typing import Any, Awaitable, Callable

import aiohttp
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from arbitrage_bot.config import Settings


class SessionMiddleware(BaseMiddleware):
    def __init__(self, session: aiohttp.ClientSession) -> None:
        super().__init__()
        self.session = session

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        data["http_session"] = self.session
        return await handler(event, data)


class SettingsMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        data["settings"] = self.settings
        return await handler(event, data)
