from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.bot_manager import bot_manager
from app.handlers.admin.filters import IsAdminFilter
from app.handlers.admin.states import ChannelStates
from app.models.channel import Channel
from app.models.enums import ChannelType
from app.repositories.channel_repository import ChannelRepository

router = Router(name="admin_channels")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


def _channels_list_keyboard(bot_id: int, channels: list[Channel]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"[{c.type.value}] {c.label}", callback_data=f"adm:channel_detail:{c.id}")]
        for c in channels
    ]
    rows.append([InlineKeyboardButton(text="➕ Add channel", callback_data=f"adm:channel_add:{bot_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:bot:{bot_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(lambda c: c.data and c.data.startswith("adm:channels:"))
async def channels_list(call: CallbackQuery, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = ChannelRepository(session)
    channels = await repo.list_for_bot(bot_id)
    await call.message.edit_text("📡 <b>Channels</b>", reply_markup=_channels_list_keyboard(bot_id, channels))
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:channel_detail:"))
async def channel_detail(call: CallbackQuery, session: AsyncSession) -> None:
    channel_id = int(call.data.split(":")[-1])
    repo = ChannelRepository(session)
    ch = await repo.get(channel_id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Delete", callback_data=f"adm:channel_delete:{ch.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:channels:{ch.bot_id}")],
        ]
    )
    verified = "✅" if ch.is_bot_admin_verified else "⚠️ bot admin status unverified"
    await call.message.edit_text(
        f"<b>{ch.label}</b>\nType: {ch.type.value}\nchat_id: <code>{ch.tg_chat_id}</code>\nURL: {ch.url}\n{verified}",
        reply_markup=keyboard,
    )
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:channel_delete:"))
async def channel_delete(call: CallbackQuery, session: AsyncSession) -> None:
    channel_id = int(call.data.split(":")[-1])
    repo = ChannelRepository(session)
    ch = await repo.get(channel_id)
    bot_id = ch.bot_id
    await repo.delete(ch)
    channels = await repo.list_for_bot(bot_id)
    await call.message.edit_text("📡 <b>Channels</b>", reply_markup=_channels_list_keyboard(bot_id, channels))
    await call.answer("Deleted.")


@router.callback_query(lambda c: c.data and c.data.startswith("adm:channel_add:"))
async def add_channel_start(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(ChannelStates.waiting_type)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t.value, callback_data=f"adm:chtype:{t.value}")] for t in ChannelType]
    )
    await call.message.edit_text("Select channel type:", reply_markup=keyboard)
    await call.answer()


@router.callback_query(ChannelStates.waiting_type, lambda c: c.data and c.data.startswith("adm:chtype:"))
async def add_channel_type(call: CallbackQuery, state: FSMContext) -> None:
    ch_type = call.data.split(":")[-1]
    await state.update_data(channel_type=ch_type)
    await state.set_state(ChannelStates.waiting_label)
    await call.message.edit_text("Send a label for this channel (shown to users, e.g. \"📰 Main News\").")
    await call.answer()


@router.message(ChannelStates.waiting_label)
async def add_channel_label(message: Message, state: FSMContext) -> None:
    await state.update_data(label=message.text.strip())
    await state.set_state(ChannelStates.waiting_chat_id)
    await message.answer(
        "Send the numeric Telegram chat_id (forward any message from that channel to @JsonDumpBot to find it), "
        "or /skip if this is a link-only channel the bot cannot verify."
    )


@router.message(ChannelStates.waiting_chat_id)
async def add_channel_chat_id(message: Message, state: FSMContext) -> None:
    chat_id = None
    if message.text.strip() != "/skip":
        try:
            chat_id = int(message.text.strip())
        except ValueError:
            await message.answer("That doesn't look like a numeric chat_id. Send digits (often starting with -100), or /skip.")
            return
    await state.update_data(chat_id=chat_id)
    await state.set_state(ChannelStates.waiting_url)
    await message.answer("Send the public URL for this channel (e.g. https://t.me/mychannel), or /skip.")


@router.message(ChannelStates.waiting_url)
async def add_channel_url(message: Message, state: FSMContext, session: AsyncSession) -> None:
    url = None if message.text.strip() == "/skip" else message.text.strip()
    data = await state.get_data()
    target_bot_id = data["target_bot_id"]
    
    child_bot = await bot_manager.get(target_bot_id)

    is_verified = False
    if data["chat_id"] is not None and child_bot:
        try:
            member = await child_bot.get_chat_member(chat_id=data["chat_id"], user_id=child_bot.id)
            is_verified = member.status in ("administrator", "creator")
        except Exception:
            is_verified = False

    repo = ChannelRepository(session)
    channel = Channel(
        bot_id=target_bot_id,
        type=ChannelType(data["channel_type"]),
        label=data["label"],
        tg_chat_id=data["chat_id"],
        url=url,
        is_bot_admin_verified=is_verified,
    )
    repo.add(channel)
    await state.clear()

    warning = "" if is_verified or data["chat_id"] is None else (
        "\n⚠️ Warning: the bot does not appear to be an admin in that chat. "
        "Subscription checks and join-request approval will fail until you add it as admin."
    )
    await message.answer(f"✅ Channel \"{channel.label}\" added.{warning}")