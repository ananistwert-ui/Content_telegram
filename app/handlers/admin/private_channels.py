from __future__ import annotations

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.admin.filters import IsAdminFilter
from app.handlers.admin.states import PrivateChannelStates
from app.models.channel import ChannelRequirement, PrivateChannel
from app.models.enums import ChannelType
from app.repositories.channel_repository import ChannelRepository, PrivateChannelRepository

router = Router(name="admin_private_channels")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


def _pc_list_keyboard(bot_id: int, pcs: list[PrivateChannel]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"⭐ {pc.title}", callback_data=f"adm:pc_detail:{pc.id}")] for pc in pcs]
    rows.append([InlineKeyboardButton(text="➕ Create private channel", callback_data=f"adm:pc_add:{bot_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:bot:{bot_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(lambda c: c.data and c.data.startswith("adm:pc:"))
async def pc_list(call: CallbackQuery, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = PrivateChannelRepository(session)
    pcs = await repo.list_for_bot(bot_id)
    await call.message.edit_text("⭐ <b>Private channels</b>", reply_markup=_pc_list_keyboard(bot_id, pcs))
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:pc_detail:"))
async def pc_detail(call: CallbackQuery, session: AsyncSession) -> None:
    pc_id = int(call.data.split(":")[-1])
    repo = PrivateChannelRepository(session)
    pc = await repo.get_with_requirements(pc_id)
    req_lines = "\n".join(f"  • {r.required_channel.label}" for r in pc.requirements) or "  (none set)"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Edit requirements", callback_data=f"adm:pc_reqs:{pc.id}")],
            [InlineKeyboardButton(text="🗑 Delete", callback_data=f"adm:pc_delete:{pc.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:pc:{pc.bot_id}")],
        ]
    )
    await call.message.edit_text(
        f"⭐ <b>{pc.title}</b>\nInvite link: {pc.invite_link or '(none)'}\nRequired channels:\n{req_lines}",
        reply_markup=keyboard,
    )
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:pc_delete:"))
async def pc_delete(call: CallbackQuery, session: AsyncSession) -> None:
    pc_id = int(call.data.split(":")[-1])
    repo = PrivateChannelRepository(session)
    pc = await repo.get(pc_id)
    bot_id = pc.bot_id
    await repo.delete(pc)
    pcs = await repo.list_for_bot(bot_id)
    await call.message.edit_text("⭐ <b>Private channels</b>", reply_markup=_pc_list_keyboard(bot_id, pcs))
    await call.answer("Deleted.")


# ---- Create wizard: title -> pick underlying PRIVATE channel -> auto invite link ----

@router.callback_query(lambda c: c.data and c.data.startswith("adm:pc_add:"))
async def pc_add_start(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(PrivateChannelStates.waiting_title)
    await call.message.edit_text(
        "Send a title for this private channel (e.g. \"VIP Gold\").\n\n"
        "Note: first add the underlying channel itself via Channels -> Add channel, "
        "using type <code>private</code>, before creating the tier here."
    )
    await call.answer()


@router.message(PrivateChannelStates.waiting_title)
async def pc_add_title(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.update_data(title=message.text.strip())
    data = await state.get_data()

    ch_repo = ChannelRepository(session)
    private_channels_raw = await ch_repo.list_for_bot(data["target_bot_id"], type_=ChannelType.PRIVATE)
    pc_repo = PrivateChannelRepository(session)
    already_wrapped_channel_ids = {pc.channel_id for pc in await pc_repo.list_for_bot(data["target_bot_id"])}
    available = [c for c in private_channels_raw if c.id not in already_wrapped_channel_ids]

    if not available:
        await state.clear()
        await message.answer(
            "No unassigned channels of type 'private' found. Add one via Channels -> Add channel "
            "(type=private) first, then retry."
        )
        return

    await state.set_state(PrivateChannelStates.waiting_channel_pick)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=c.label, callback_data=f"adm:pc_pick_channel:{c.id}")] for c in available]
    )
    await message.answer("Pick the underlying channel:", reply_markup=keyboard)


@router.callback_query(PrivateChannelStates.waiting_channel_pick, lambda c: c.data and c.data.startswith("adm:pc_pick_channel:"))
async def pc_pick_channel(call: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    channel_id = int(call.data.split(":")[-1])
    ch_repo = ChannelRepository(session)
    channel = await ch_repo.get(channel_id)
    data = await state.get_data()

    invite_link = None
    try:
        link_obj = await bot.create_chat_invite_link(
            chat_id=channel.tg_chat_id,
            name=data["title"][:32],
            creates_join_request=True,
        )
        invite_link = link_obj.invite_link
    except TelegramAPIError as exc:
        await call.message.edit_text(
            f"⚠️ Could not create a join-request invite link: {exc}\n"
            "Make sure the bot is an admin in that channel with invite permissions, then try again."
        )
        await call.answer()
        return

    pc_repo = PrivateChannelRepository(session)
    pc = PrivateChannel(
        bot_id=data["target_bot_id"],
        channel_id=channel.id,
        title=data["title"],
        invite_link=invite_link,
    )
    pc_repo.add(pc)
    await state.clear()
    await call.message.edit_text(f"✅ Private channel \"{pc.title}\" created with a join-request invite link.")
    await call.answer()


# ---- Requirements multi-select toggle ----

@router.callback_query(lambda c: c.data and c.data.startswith("adm:pc_reqs:"))
async def pc_reqs_menu(call: CallbackQuery, session: AsyncSession) -> None:
    pc_id = int(call.data.split(":")[-1])
    pc_repo = PrivateChannelRepository(session)
    pc = await pc_repo.get_with_requirements(pc_id)
    ch_repo = ChannelRepository(session)
    all_channels = await ch_repo.list_for_bot(pc.bot_id)
    required_ids = {r.required_channel_id for r in pc.requirements}

    rows = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if c.id in required_ids else '⬜️'} {c.label}",
                callback_data=f"adm:pc_req_toggle:{pc.id}:{c.id}",
            )
        ]
        for c in all_channels
        if c.type != ChannelType.PRIVATE
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:pc_detail:{pc.id}")])
    await call.message.edit_text(
        f"Toggle required channels for <b>{pc.title}</b>:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:pc_req_toggle:"))
async def pc_req_toggle(call: CallbackQuery, session: AsyncSession) -> None:
    _, _, pc_id_str, channel_id_str = call.data.split(":")
    pc_id, channel_id = int(pc_id_str), int(channel_id_str)

    pc_repo = PrivateChannelRepository(session)
    pc = await pc_repo.get_with_requirements(pc_id)
    existing = next((r for r in pc.requirements if r.required_channel_id == channel_id), None)

    if existing:
        await session.delete(existing)
    else:
        session.add(ChannelRequirement(private_channel_id=pc_id, required_channel_id=channel_id))
    await session.flush()
    await call.answer("Updated.")
    await pc_reqs_menu(call, session)
