from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.admin.filters import IsAdminFilter
from app.handlers.admin.states import MenuButtonStates
from app.keyboards.builders import build_main_menu_keyboard
from app.models.enums import ButtonType
from app.models.menu import MenuButton
from app.repositories.menu_repository import MenuRepository

router = Router(name="admin_menu_buttons")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


def _menu_list_keyboard(bot_id: int, buttons: list[MenuButton]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{'👁' if b.is_visible else '🚫'} {b.text}", callback_data=f"adm:menu_btn:{b.id}"
            )
        ]
        for b in buttons
    ]
    rows.append([InlineKeyboardButton(text="➕ Add button", callback_data=f"adm:menu_add:{bot_id}")])
    rows.append([InlineKeyboardButton(text="👁 Preview menu", callback_data=f"adm:menu_preview:{bot_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:bot:{bot_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(lambda c: c.data and c.data.startswith("adm:menu:"))
async def menu_list(call: CallbackQuery, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = MenuRepository(session)
    buttons = await repo.list_for_bot(bot_id, visible_only=False)
    await call.message.edit_text("📋 <b>Menu buttons</b>", reply_markup=_menu_list_keyboard(bot_id, buttons))
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:menu_preview:"))
async def menu_preview(call: CallbackQuery, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = MenuRepository(session)
    buttons = await repo.list_for_bot(bot_id)
    await call.message.answer("Preview:", reply_markup=build_main_menu_keyboard(buttons))
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:menu_btn:"))
async def button_detail(call: CallbackQuery, session: AsyncSession) -> None:
    btn_id = int(call.data.split(":")[-1])
    repo = MenuRepository(session)
    btn = await repo.get(btn_id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Toggle visible", callback_data=f"adm:menu_toggle:{btn.id}")],
            [InlineKeyboardButton(text="🗑 Delete", callback_data=f"adm:menu_delete:{btn.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:menu:{btn.bot_id}")],
        ]
    )
    await call.message.edit_text(
        f"Button: <b>{btn.text}</b>\nType: {btn.type.value}\nRow: {btn.row}, Position: {btn.position}\nPayload: <code>{btn.payload}</code>",
        reply_markup=keyboard,
    )
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:menu_toggle:"))
async def toggle_visible(call: CallbackQuery, session: AsyncSession) -> None:
    btn_id = int(call.data.split(":")[-1])
    repo = MenuRepository(session)
    btn = await repo.get(btn_id)
    btn.is_visible = not btn.is_visible
    await call.answer("Updated.")
    await button_detail(call, session)


@router.callback_query(lambda c: c.data and c.data.startswith("adm:menu_delete:"))
async def delete_button(call: CallbackQuery, session: AsyncSession) -> None:
    btn_id = int(call.data.split(":")[-1])
    repo = MenuRepository(session)
    btn = await repo.get(btn_id)
    bot_id = btn.bot_id
    await repo.delete(btn)
    buttons = await repo.list_for_bot(bot_id, visible_only=False)
    await call.message.edit_text("📋 <b>Menu buttons</b>", reply_markup=_menu_list_keyboard(bot_id, buttons))
    await call.answer("Deleted.")


# ---- Add-button wizard: text -> type -> type-specific payload -> row/position ----

@router.callback_query(lambda c: c.data and c.data.startswith("adm:menu_add:"))
async def add_button_start(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(MenuButtonStates.waiting_text)
    await call.message.edit_text("Send the button text (e.g. \"📡 News\").")
    await call.answer()


@router.message(MenuButtonStates.waiting_text)
async def add_button_text(message: Message, state: FSMContext) -> None:
    await state.update_data(text=message.text.strip())
    await state.set_state(MenuButtonStates.waiting_type)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 URL", callback_data="adm:btntype:url")],
            [InlineKeyboardButton(text="💬 External chat", callback_data="adm:btntype:external_chat")],
            [InlineKeyboardButton(text="⚙️ Callback (subscribe/etc.)", callback_data="adm:btntype:callback")],
        ]
    )
    await message.answer("What type of button is this?", reply_markup=keyboard)


@router.callback_query(MenuButtonStates.waiting_type, lambda c: c.data and c.data.startswith("adm:btntype:"))
async def add_button_type(call: CallbackQuery, state: FSMContext) -> None:
    btn_type = call.data.split(":")[-1]
    await state.update_data(btn_type=btn_type)
    if btn_type == ButtonType.URL.value:
        await state.set_state(MenuButtonStates.waiting_url)
        await call.message.edit_text("Send the target URL (e.g. the news channel link).")
    elif btn_type == ButtonType.EXTERNAL_CHAT.value:
        await state.set_state(MenuButtonStates.waiting_external_username)
        await call.message.edit_text("Send the target @username to open a chat with.")
    else:
        await state.set_state(MenuButtonStates.waiting_row_position)
        await state.update_data(payload={"action": "subscribe"})
        await call.message.edit_text(
            "Send row and position as two numbers separated by a space, e.g. \"0 0\" for top-left."
        )
    await call.answer()


@router.message(MenuButtonStates.waiting_url)
async def add_button_url(message: Message, state: FSMContext) -> None:
    await state.update_data(payload={"url": message.text.strip()})
    await state.set_state(MenuButtonStates.waiting_row_position)
    await message.answer("Send row and position as two numbers separated by a space, e.g. \"0 0\".")


@router.message(MenuButtonStates.waiting_external_username)
async def add_button_external_username(message: Message, state: FSMContext) -> None:
    await state.update_data(payload={"username": message.text.strip()})
    await state.set_state(MenuButtonStates.waiting_external_prefilled)
    await message.answer("Send the prefilled message text (or /skip for none).")


@router.message(MenuButtonStates.waiting_external_prefilled)
async def add_button_prefilled(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    payload = data["payload"]
    if message.text.strip() != "/skip":
        payload["prefilled_text"] = message.text.strip()
    await state.update_data(payload=payload)
    await state.set_state(MenuButtonStates.waiting_row_position)
    await message.answer("Send row and position as two numbers separated by a space, e.g. \"0 0\".")


@router.message(MenuButtonStates.waiting_row_position)
async def add_button_finish(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        row_str, pos_str = message.text.strip().split()
        row, position = int(row_str), int(pos_str)
    except ValueError:
        await message.answer("Please send two numbers separated by a space, e.g. \"0 0\".")
        return

    data = await state.get_data()
    repo = MenuRepository(session)
    button = MenuButton(
        bot_id=data["target_bot_id"],
        text=data["text"],
        type=ButtonType(data["btn_type"]),
        payload=data["payload"],
        row=row,
        position=position,
    )
    repo.add(button)
    await state.clear()
    await message.answer(f"✅ Button \"{button.text}\" added.")
