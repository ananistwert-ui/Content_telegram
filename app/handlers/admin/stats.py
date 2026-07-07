from __future__ import annotations

import datetime as dt

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.admin.filters import IsAdminFilter
from app.models.enums import AnalyticsEventType
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.user_repository import UserRepository

router = Router(name="admin_stats")
router.callback_query.filter(IsAdminFilter())


@router.callback_query(lambda c: c.data == "adm:stats")
async def stats_pick_bot(call: CallbackQuery, session: AsyncSession) -> None:
    repo = BotRepository(session)
    bots = await repo.list_active_child_bots()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=b.display_name, callback_data=f"adm:stats_bot:{b.id}")] for b in bots]
        + [[InlineKeyboardButton(text="🌍 Global comparison", callback_data="adm:stats_global")]]
        + [[InlineKeyboardButton(text="⬅️ Back", callback_data="adm:home")]]
    )
    await call.message.edit_text("📊 <b>Statistics</b>\nPick a bot, or view the global comparison.", reply_markup=keyboard)
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:stats_bot:"))
async def stats_for_bot(call: CallbackQuery, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    bot_repo = BotRepository(session)
    bot_row = await bot_repo.get(bot_id)

    users = UserRepository(session)
    analytics = AnalyticsRepository(session)

    total_users = await users.count_total(bot_id)
    captcha_passed = await users.count_captcha_passed(bot_id)
    active_7d = await users.count_active_since(bot_id, dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7))
    joins_approved = await analytics.count_event(bot_id, AnalyticsEventType.JOIN_REQUEST_APPROVED)
    private_requests = await analytics.count_event(bot_id, AnalyticsEventType.PRIVATE_CHANNEL_REQUESTED)

    conversion = f"{(joins_approved / private_requests * 100):.1f}%" if private_requests else "n/a"

    text = (
        f"📊 <b>{bot_row.display_name}</b>\n\n"
        f"Total users: <b>{total_users}</b>\n"
        f"Captcha passed: <b>{captcha_passed}</b>\n"
        f"Active last 7 days: <b>{active_7d}</b>\n"
        f"Private channel requests: <b>{private_requests}</b>\n"
        f"Private channel joins approved: <b>{joins_approved}</b>\n"
        f"Request → join conversion: <b>{conversion}</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="adm:stats")]])
    await call.message.edit_text(text, reply_markup=keyboard)
    await call.answer()


@router.callback_query(lambda c: c.data == "adm:stats_global")
async def stats_global(call: CallbackQuery, session: AsyncSession) -> None:
    bot_repo = BotRepository(session)
    analytics = AnalyticsRepository(session)
    users = UserRepository(session)

    bots = await bot_repo.list_active_child_bots()
    leads_by_bot = dict(await analytics.leads_per_bot())

    lines = ["🌍 <b>Global bot comparison</b>\n"]
    total_all = 0
    for b in bots:
        total = await users.count_total(b.id)
        total_all += total
        leads = leads_by_bot.get(b.id, 0)
        lines.append(f"• <b>{b.display_name}</b>: {total} users, {leads} /start leads")
    lines.append(f"\nTotal users across all bots: <b>{total_all}</b>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="adm:stats")]])
    await call.message.edit_text("\n".join(lines), reply_markup=keyboard)
    await call.answer()
