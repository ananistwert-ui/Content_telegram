from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db.redis import get_redis
from app.repositories.bot_repository import BotRepository

logger = logging.getLogger(__name__)

_CONFIG_CACHE_TTL = 60  # seconds -- admin edits are picked up within a minute


class BotContextMiddleware(BaseMiddleware):
    """Resolves which `Bot` row (and its BotConfig) this update belongs to,
    based on the aiogram Bot's numeric Telegram id, and injects both into
    `data`. This is what lets every handler stay bot-agnostic: it reads
    `data["db_bot"]` / `data["db_bot_config"]` instead of hardcoding
    anything.

    Cached in Redis because this middleware runs on every single update
    across every bot -- a DB round trip per update would be wasteful.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        aiogram_bot = data["bot"]
        session = data["session"]
        tg_bot_id = aiogram_bot.id

        redis = get_redis()
        cache_key = f"botctx:{tg_bot_id}"
        cached = await redis.get(cache_key)

        bot_repo = BotRepository(session)
        if cached:
            bot_row_id = json.loads(cached)["bot_row_id"]
            db_bot = await bot_repo.get_with_config(bot_row_id)
        else:
            me = await aiogram_bot.me()
            db_bot = await bot_repo.get_by_token(aiogram_bot.token)
            if db_bot is None:
                logger.error("No Bot row registered for token of @%s -- rejecting update", me.username)
                return None
            await redis.set(cache_key, json.dumps({"bot_row_id": db_bot.id}), ex=_CONFIG_CACHE_TTL)

        if db_bot is None or not db_bot.is_active:
            logger.warning("Update received for inactive/unregistered bot tg_id=%s", tg_bot_id)
            return None

        data["db_bot"] = db_bot
        data["db_bot_config"] = db_bot.config
        return await handler(event, data)
