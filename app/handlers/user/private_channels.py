from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.keyboards.builders import build_join_link_keyboard, build_missing_requirements_keyboard
from app.models.bot import Bot as BotModel
from app.repositories.channel_repository import PrivateChannelRepository
from app.repositories.user_repository import UserRepository
from app.services.private_channel_service import PrivateChannelService
from app.services.subscription_service import SubscriptionService

router = Router(name="user_private_channels")


def _pc_service(bot: Bot, session: AsyncSession) -> PrivateChannelService:
    subscription_service = SubscriptionService(bot, session, get_redis())
    return PrivateChannelService(session, subscription_service)


@router.callback_query(lambda c: c.data and c.data.startswith("private_channel:"))
async def on_private_channel_selected(
    call: CallbackQuery, bot: Bot, session: AsyncSession, db_bot: BotModel
) -> None:
    pc_id = int(call.data.split(":", 1)[1])
    await _evaluate_and_respond(call, bot, session, db_bot, pc_id, is_recheck=False)


@router.callback_query(lambda c: c.data and c.data.startswith("recheck_pc:"))
async def on_recheck(call: CallbackQuery, bot: Bot, session: AsyncSession, db_bot: BotModel) -> None:
    pc_id = int(call.data.split(":", 1)[1])
    await _evaluate_and_respond(call, bot, session, db_bot, pc_id, is_recheck=True)


async def _evaluate_and_respond(
    call: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    db_bot: BotModel,
    pc_id: int,
    is_recheck: bool,
) -> None:
    users = UserRepository(session)
    user = await users.get_by_tg_id(db_bot.id, call.from_user.id)
    if user is None:
        await call.answer("Please press /start first.", show_alert=True)
        return

    pc_repo = PrivateChannelRepository(session)
    private_channel = await pc_repo.get_with_requirements(pc_id)
    if private_channel is None or private_channel.bot_id != db_bot.id:
        await call.answer("This private channel no longer exists.", show_alert=True)
        return

    service = _pc_service(bot, session)
    result = await service.request_access(bot, user, private_channel)

    if result.granted:
        if not private_channel.invite_link:
            await call.answer(
                "This channel is not fully configured yet (missing invite link). Contact the admin.",
                show_alert=True,
            )
            return
        text = f"✅ You're eligible for {private_channel.title}! Tap below to join."
        keyboard = build_join_link_keyboard(private_channel.invite_link, private_channel.title)
        if is_recheck:
            await call.message.edit_text(text, reply_markup=keyboard)
        else:
            await call.message.answer(text, reply_markup=keyboard)
    else:
        text = "❌ You need to subscribe to the following first:"
        keyboard = build_missing_requirements_keyboard(result.missing_channels, recheck_callback=f"recheck_pc:{pc_id}")
        if is_recheck:
            await call.message.edit_text(text, reply_markup=keyboard)
        else:
            await call.message.answer(text, reply_markup=keyboard)

    await call.answer()
