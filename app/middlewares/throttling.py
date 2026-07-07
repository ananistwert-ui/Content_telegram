from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db.redis import get_redis


class ThrottlingMiddleware(BaseMiddleware):
    """Drops updates from a (bot, user) pair that fire faster than
    `rate` seconds apart. Prevents captcha-button mashing and menu-spam
    from degrading the shared worker pool under ~5000 concurrent users.
    """

    def __init__(self, rate: float = 0.5) -> None:
        self.rate = rate

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        bot_id = data["bot"].id
        redis = get_redis()
        key = f"throttle:{bot_id}:{user.id}"
        px = max(int(self.rate * 1000), 1)
        acquired = await redis.set(key, "1", px=px, nx=True)
        if not acquired:
            return None
        return await handler(event, data)
