from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.handlers.user.start import send_welcome_and_menu
from app.keyboards.builders import build_captcha_keyboard
from app.models.bot import Bot as BotModel, BotConfig
from app.models.enums import AnalyticsEventType
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.user_repository import UserRepository
from app.services.captcha_service import CaptchaService

router = Router(name="user_captcha")


@router.callback_query(lambda c: c.data and c.data.startswith("captcha:"))
async def on_captcha_answer(
    call: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    db_bot: BotModel,
    db_bot_config: BotConfig,
) -> None:
    chosen_emoji = call.data.split(":", 1)[1]
    redis: Redis = get_redis()

    users = UserRepository(session)
    analytics = AnalyticsRepository(session)
    user = await users.get_by_tg_id(db_bot.id, call.from_user.id)
    if user is None:
        await call.answer("Session expired, please press /start again.", show_alert=True)
        return

    expected = await redis.get(f"captcha_state:{db_bot.id}:{call.from_user.id}")
    correct = expected is not None and chosen_emoji == expected

    if correct:
        user.captcha_passed = True
        await call.answer("✅ Correct!")
        await analytics.log(bot_id=db_bot.id, user_id=user.id, event_type=AnalyticsEventType.CAPTCHA_PASSED)
        await call.message.delete()
        await send_welcome_and_menu(call.message, bot, session, db_bot.id, db_bot_config)
        await analytics.log(bot_id=db_bot.id, user_id=user.id, event_type=AnalyticsEventType.MENU_SHOWN)
    else:
        user.captcha_attempts += 1
        await analytics.log(bot_id=db_bot.id, user_id=user.id, event_type=AnalyticsEventType.CAPTCHA_FAILED)
        await call.answer("❌ Wrong, try again.", show_alert=False)
        # Re-shuffle so the same emoji isn't always in the same spot,
        # and refresh the expected-answer TTL for the retry.
        options = CaptchaService.shuffled_options(db_bot_config)
        await redis.set(
            f"captcha_state:{db_bot.id}:{call.from_user.id}",
            db_bot_config.captcha_correct_emoji,
            ex=600,
        )
        await call.message.edit_reply_markup(reply_markup=build_captcha_keyboard(db_bot_config, options))