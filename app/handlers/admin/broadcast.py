from __future__ import annotations

import datetime as dt

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.handlers.admin.filters import IsAdminFilter
from app.handlers.admin.states import BroadcastStates
from app.models.broadcast import Broadcast
from app.models.enums import BroadcastContentType, BroadcastStatus
from app.repositories.bot_repository import BotRepository
from app.repositories.broadcast_repository import BroadcastRepository
from app.services.broadcast_service import BroadcastService

router = Router(name="admin_broadcast")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


async def _enqueue(broadcast_id: int, run_at: dt.datetime | None = None) -> None:
    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_DSN))
    try:
        if run_at is None:
            await pool.enqueue_job("send_broadcast_task", broadcast_id)
        # If run_at is set we don't enqueue here -- the cron sweep in the
        # worker picks it up once `scheduled_at` arrives (see tasks.py).
    finally:
        await pool.close()


@router.callback_query(lambda c: c.data == "adm:broadcast")
async def broadcast_pick_bot(call: CallbackQuery, session: AsyncSession) -> None:
    repo = BotRepository(session)
    bots = await repo.list_active_child_bots()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=b.display_name, callback_data=f"adm:broadcast_bot:{b.id}")] for b in bots]
        + [[InlineKeyboardButton(text="⬅️ Back", callback_data="adm:home")]]
    )
    await call.message.edit_text("📢 Which bot's audience do you want to broadcast to?", reply_markup=keyboard)
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:broadcast_bot:"))
async def broadcast_start(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(BroadcastStates.waiting_content)
    await call.message.edit_text(
        "Send the broadcast content now: plain text, or a photo/video/GIF with an optional caption."
    )
    await call.answer()


@router.message(BroadcastStates.waiting_content)
async def broadcast_receive_content(message: Message, state: FSMContext) -> None:
    if message.photo:
        content_type, media_file_id, caption = BroadcastContentType.PHOTO, message.photo[-1].file_id, message.html_text
    elif message.video:
        content_type, media_file_id, caption = BroadcastContentType.VIDEO, message.video.file_id, message.html_text
    elif message.animation:
        content_type, media_file_id, caption = BroadcastContentType.GIF, message.animation.file_id, message.html_text
    else:
        content_type, media_file_id, caption = BroadcastContentType.TEXT, None, message.html_text

    await state.update_data(content_type=content_type.value, media_file_id=media_file_id, caption=caption)
    await state.set_state(BroadcastStates.waiting_buttons)
    await message.answer(
        "Add inline buttons now, one per line as `Text | https://url`, or /skip for none."
    )


@router.message(BroadcastStates.waiting_buttons)
async def broadcast_receive_buttons(message: Message, state: FSMContext) -> None:
    inline_buttons: list[list[dict]] = []
    if message.text.strip() != "/skip":
        for line in message.text.strip().splitlines():
            if "|" not in line:
                continue
            text, url = (part.strip() for part in line.split("|", 1))
            inline_buttons.append([{"text": text, "url": url}])

    await state.update_data(inline_buttons=inline_buttons)
    await state.set_state(BroadcastStates.waiting_schedule_choice)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Send now", callback_data="adm:bc_send_now")],
            [InlineKeyboardButton(text="🕒 Schedule", callback_data="adm:bc_schedule")],
        ]
    )
    await message.answer("Ready. Send now, or schedule for later?", reply_markup=keyboard)


@router.callback_query(BroadcastStates.waiting_schedule_choice, lambda c: c.data == "adm:bc_schedule")
async def broadcast_ask_datetime(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastStates.waiting_schedule_datetime)
    await call.message.edit_text("Send the date/time (UTC) as YYYY-MM-DD HH:MM.")
    await call.answer()


@router.message(BroadcastStates.waiting_schedule_datetime)
async def broadcast_receive_datetime(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        scheduled_at = dt.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        await message.answer("Invalid format. Use YYYY-MM-DD HH:MM (UTC).")
        return
    await _finalize_broadcast(message, state, session, scheduled_at=scheduled_at)


@router.callback_query(BroadcastStates.waiting_schedule_choice, lambda c: c.data == "adm:bc_send_now")
async def broadcast_send_now(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await _finalize_broadcast(call.message, state, session, scheduled_at=None)
    await call.answer()


async def _finalize_broadcast(
    message: Message, state: FSMContext, session: AsyncSession, scheduled_at: dt.datetime | None
) -> None:
    data = await state.get_data()
    broadcast = Broadcast(
        bot_id=data["target_bot_id"],
        content_type=BroadcastContentType(data["content_type"]),
        media_file_id=data.get("media_file_id"),
        caption=data.get("caption"),
        inline_buttons=data.get("inline_buttons", []),
        status=BroadcastStatus.SCHEDULED if scheduled_at else BroadcastStatus.DRAFT,
        scheduled_at=scheduled_at,
    )
    repo = BroadcastRepository(session)
    repo.add(broadcast)
    await repo.flush()

    service = BroadcastService(session)
    recipient_count = await service.create_jobs(broadcast)
    await state.clear()

    if scheduled_at:
        await message.answer(
            f"✅ Broadcast scheduled for {scheduled_at:%Y-%m-%d %H:%M} UTC to {recipient_count} recipients."
        )
    else:
        await _enqueue(broadcast.id)
        await message.answer(f"🚀 Broadcast enqueued for {recipient_count} recipients.")
