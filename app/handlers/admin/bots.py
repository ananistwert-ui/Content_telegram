from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.admin.common import bot_detail_keyboard, bots_list_keyboard, set_selected_bot_id
from app.handlers.admin.filters import IsAdminFilter
from app.handlers.admin.states import RegisterBotStates
from app.repositories.bot_repository import BotRepository
from app.services.bot_orchestration_service import BotOrchestrationService, BotRegistrationError

router = Router(name="admin_bots")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.callback_query(lambda c: c.data == "adm:bots")
async def list_bots(call: CallbackQuery, session: AsyncSession) -> None:
    repo = BotRepository(session)
    bots = await repo.list_active_child_bots()
    await call.message.edit_text("🤖 <b>Child bots</b>", reply_markup=bots_list_keyboard(bots))
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:bot:"))
async def bot_detail(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = BotRepository(session)
    bot_row = await repo.get_with_config(bot_id)
    if bot_row is None:
        await call.answer("Bot not found.", show_alert=True)
        return
    await set_selected_bot_id(state, bot_id)
    await call.message.edit_text(
        f"🤖 <b>{bot_row.display_name}</b> (@{bot_row.username})\nStatus: {'🟢 active' if bot_row.is_active else '🔴 disabled'}",
        reply_markup=bot_detail_keyboard(bot_row),
    )
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:bot_toggle:"))
async def toggle_bot(call: CallbackQuery, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = BotRepository(session)
    bot_row = await repo.get_with_config(bot_id)
    if bot_row is None:
        await call.answer("Bot not found.", show_alert=True)
        return
    orchestrator = BotOrchestrationService(session)
    bot_row = await orchestrator.toggle_active(bot_row)
    await call.message.edit_reply_markup(reply_markup=bot_detail_keyboard(bot_row))
    await call.answer("Updated.")


@router.callback_query(lambda c: c.data == "adm:bot_register")
async def start_registration(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RegisterBotStates.waiting_token)
    await call.message.edit_text("Send me the new bot's token (from @BotFather).")
    await call.answer()


@router.message(RegisterBotStates.waiting_token)
async def receive_token(message: Message, state: FSMContext) -> None:
    await state.update_data(new_bot_token=message.text.strip())
    await state.set_state(RegisterBotStates.waiting_display_name)
    await message.answer("Now send a display name for this bot (for your own reference in this admin panel).")


@router.message(RegisterBotStates.waiting_display_name)
async def receive_display_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    token = data["new_bot_token"]
    display_name = message.text.strip()

    orchestrator = BotOrchestrationService(session)
    try:
        bot_row = await orchestrator.register(token, display_name)
    except BotRegistrationError as exc:
        await message.answer(f"⚠️ {exc}\nSend the token again, or /start to cancel.")
        return

    await state.clear()
    await message.answer(
        f"✅ Bot <b>{bot_row.display_name}</b> (@{bot_row.username}) registered and webhook is live."
    )
