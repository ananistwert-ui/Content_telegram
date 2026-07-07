from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.builders import build_private_channels_keyboard
from app.models.bot import Bot as BotModel
from app.repositories.user_repository import UserRepository
from app.services.private_channel_service import PrivateChannelService
from app.services.subscription_service import SubscriptionService

router = Router(name="user_menu")


@router.callback_query(lambda c: c.data and c.data.startswith("menu:"))
async def on_menu_action(
    call: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    db_bot: BotModel,
) -> None:
    _, action, _button_id = call.data.split(":", 2)

    if action == "subscribe":
        await _show_private_channels(call, bot, session, db_bot)
        return

    await call.answer()


async def _show_private_channels(call: CallbackQuery, bot: Bot, session: AsyncSession, db_bot: BotModel) -> None:
    from app.db.redis import get_redis

    subscription_service = SubscriptionService(bot, session, get_redis())
    pc_service = PrivateChannelService(session, subscription_service)

    private_channels = await pc_service.list_private_channels(db_bot.id)
    if not private_channels:
        await call.answer("No private channels are configured yet.", show_alert=True)
        return

    keyboard = build_private_channels_keyboard(private_channels)
    await call.message.answer("Choose a private channel:", reply_markup=keyboard)
    await call.answer()
