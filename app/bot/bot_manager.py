from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.db.session import AsyncSessionFactory
from app.repositories.bot_repository import BotRepository

logger = logging.getLogger(__name__)


class BotManager:
    """Caches one aiogram `Bot` instance per DB bot id, created lazily on
    first webhook hit and reused after that (so we don't spin up a new
    aiohttp client session per update). Thread-unsafe-by-design is fine
    here since we run a single asyncio event loop.
    """

    def __init__(self) -> None:
        self._bots: dict[int, Bot] = {}
        self._lock = asyncio.Lock()

    async def get(self, db_bot_id: int) -> Bot | None:
        if db_bot_id in self._bots:
            return self._bots[db_bot_id]

        async with self._lock:
            if db_bot_id in self._bots:  # re-check after acquiring lock
                return self._bots[db_bot_id]

            async with AsyncSessionFactory() as session:
                repo = BotRepository(session)
                db_bot = await repo.get(db_bot_id)
                if db_bot is None or not db_bot.is_active:
                    return None

            bot = Bot(token=db_bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            self._bots[db_bot_id] = bot
            logger.info("Instantiated Bot for db_bot_id=%s (@%s)", db_bot_id, db_bot.username)
            return bot

    async def close_all(self) -> None:
        for bot in self._bots.values():
            await bot.session.close()


bot_manager = BotManager()
