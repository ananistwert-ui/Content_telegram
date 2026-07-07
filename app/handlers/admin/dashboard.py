from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.handlers.admin.common import admin_main_menu_keyboard
from app.handlers.admin.filters import IsAdminFilter

router = Router(name="admin_dashboard")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(CommandStart())
async def admin_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🛠 <b>Admin Control Center</b>\nManage your bot ecosystem below.",
        reply_markup=admin_main_menu_keyboard(),
    )


@router.callback_query(lambda c: c.data == "adm:home")
async def back_home(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("🛠 <b>Admin Control Center</b>", reply_markup=admin_main_menu_keyboard())
    await call.answer()
