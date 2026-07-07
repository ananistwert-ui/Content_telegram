from __future__ import annotations

import logging

from aiogram import Bot as AiogramBot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.bot import Bot, BotConfig
from app.repositories.bot_repository import BotRepository

logger = logging.getLogger(__name__)


class BotRegistrationError(Exception):
    pass


class BotOrchestrationService:
    """Handles the lifecycle of a child bot: token validation, DB
    registration with sane config defaults, and webhook wiring. This is
    what makes "register a bot" in the admin UI actually bring the bot
    online without a redeploy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bots = BotRepository(session)

    async def register(self, token: str, display_name: str) -> Bot:
        existing = await self.bots.get_by_token(token)
        if existing is not None:
            raise BotRegistrationError("This token is already registered.")

        temp_bot = AiogramBot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            me = await temp_bot.get_me()
        except TelegramAPIError as exc:
            raise BotRegistrationError(f"Invalid bot token: {exc}") from exc
        finally:
            await temp_bot.session.close()

        db_bot = Bot(token=token, username=me.username, display_name=display_name, is_master=False, is_active=True)
        self.bots.add(db_bot)
        await self.bots.flush()

        db_bot.config = BotConfig(
            bot_id=db_bot.id,
            welcome_caption="👋 Welcome!",
            captcha_caption="Select {emoji}",
        )
        self.session.add(db_bot.config)
        await self.bots.flush()

        await self._set_webhook(token, db_bot.id)
        return db_bot

    async def toggle_active(self, bot_row: Bot) -> Bot:
        bot_row.is_active = not bot_row.is_active
        if bot_row.is_active:
            await self._set_webhook(bot_row.token, bot_row.id)
        else:
            await self._delete_webhook(bot_row.token)
        await self.bots.flush()
        return bot_row

    async def _set_webhook(self, token: str, bot_id: int) -> None:
        bot = AiogramBot(token=token)
        try:
            url = f"{settings.BASE_WEBHOOK_URL}/webhook/{bot_id}"
            await bot.set_webhook(
                url=url,
                secret_token=settings.WEBHOOK_SECRET,
                allowed_updates=["message", "callback_query", "chat_join_request"],
                drop_pending_updates=False,
            )
            logger.info("Webhook set for bot_id=%s -> %s", bot_id, url)
        finally:
            await bot.session.close()

    async def _delete_webhook(self, token: str) -> None:
        bot = AiogramBot(token=token)
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        finally:
            await bot.session.close()
