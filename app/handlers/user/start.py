from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.keyboards.builders import build_captcha_keyboard, build_main_menu_keyboard
from app.models.bot import Bot as BotModel, BotConfig
from app.models.enums import AnalyticsEventType
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.menu_repository import MenuRepository
from app.repositories.user_repository import UserRepository
from app.services.captcha_service import CaptchaService

logger = logging.getLogger(__name__)
router = Router(name="user_start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    db_bot: BotModel,
    db_bot_config: BotConfig,
) -> None:
    users = UserRepository(session)
    analytics = AnalyticsRepository(session)

    user = await users.get_or_create(
        bot_id=db_bot.id,
        tg_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await analytics.log(bot_id=db_bot.id, user_id=user.id, event_type=AnalyticsEventType.BOT_STARTED)

    if db_bot_config.captcha_enabled and not user.captcha_passed:
        await send_captcha(message, bot, db_bot.id, db_bot_config)
        await analytics.log(bot_id=db_bot.id, user_id=user.id, event_type=AnalyticsEventType.CAPTCHA_SHOWN)
        return

    await send_welcome_and_menu(message, bot, session, db_bot.id, db_bot_config)


async def send_captcha(message: Message, bot: Bot, bot_id: int, config: BotConfig) -> None:
    redis: Redis = get_redis()
    options = CaptchaService.shuffled_options(config)
    # Persist the shuffled order + correct answer for this exact card so the
    # callback handler validates against what was actually shown, not the
    # (possibly re-shuffled) config -- avoids a race if admin edits mid-flow.
    await redis.set(
        f"captcha_state:{bot_id}:{message.from_user.id}",
        config.captcha_correct_emoji,
        ex=600,
    )
    keyboard = build_captcha_keyboard(config, options)

    if config.captcha_photo_file_id:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=config.captcha_photo_file_id,
            caption=config.captcha_caption,
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(chat_id=message.chat.id, text=config.captcha_caption, reply_markup=keyboard)


async def send_welcome_and_menu(
    message: Message, bot: Bot, session: AsyncSession, bot_id: int, config: BotConfig
) -> None:
    menu_repo = MenuRepository(session)
    buttons = await menu_repo.list_for_bot(bot_id)
    keyboard = build_main_menu_keyboard(buttons)

    caption = config.welcome_caption or " "
    if config.welcome_photo_file_id:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=config.welcome_photo_file_id,
            caption=caption,
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(chat_id=message.chat.id, text=caption, reply_markup=keyboard)
