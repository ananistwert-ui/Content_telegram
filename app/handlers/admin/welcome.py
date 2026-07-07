from __future__ import annotations

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.admin.filters import IsAdminFilter
from app.handlers.admin.states import WelcomeEditStates
from app.repositories.bot_repository import BotConfigRepository

router = Router(name="admin_welcome")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


def _welcome_menu_keyboard(bot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Change photo", callback_data=f"adm:welcome_photo:{bot_id}")],
            [InlineKeyboardButton(text="✏️ Change caption", callback_data=f"adm:welcome_caption:{bot_id}")],
            [InlineKeyboardButton(text="👁 Preview", callback_data=f"adm:welcome_preview:{bot_id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:bot:{bot_id}")],
        ]
    )


@router.callback_query(lambda c: c.data and c.data.startswith("adm:welcome:"))
async def welcome_menu(call: CallbackQuery) -> None:
    bot_id = int(call.data.split(":")[-1])
    await call.message.edit_text("✏️ <b>Welcome message</b>", reply_markup=_welcome_menu_keyboard(bot_id))
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:welcome_photo:"))
async def ask_photo(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(WelcomeEditStates.waiting_photo)
    await call.message.edit_text("Send the new welcome photo now.")
    await call.answer()


@router.message(WelcomeEditStates.waiting_photo)
async def receive_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.photo:
        await message.answer("Please send a photo.")
        return
    data = await state.get_data()
    bot_id = data["target_bot_id"]
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(bot_id)
    config.welcome_photo_file_id = message.photo[-1].file_id
    await state.clear()
    await message.answer("✅ Welcome photo updated.")


@router.callback_query(lambda c: c.data and c.data.startswith("adm:welcome_caption:"))
async def ask_caption(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(WelcomeEditStates.waiting_caption)
    await call.message.edit_text(
        "Send the new welcome caption. Telegram formatting supported: "
        "<b>bold</b>, <i>italic</i>, <u>underline</u>, <tg-spoiler>spoiler</tg-spoiler>, "
        "<blockquote>quote</blockquote>. Send as HTML-formatted text."
    )
    await call.answer()


@router.message(WelcomeEditStates.waiting_caption)
async def receive_caption(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    bot_id = data["target_bot_id"]
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(bot_id)
    # message.html_text preserves the formatting entities the admin sent
    # (bold/italic/spoiler/custom emoji/etc) as Telegram-native HTML,
    # which is exactly what we store and later re-send verbatim.
    config.welcome_caption = message.html_text
    await state.clear()
    await message.answer("✅ Welcome caption updated.")


@router.callback_query(lambda c: c.data and c.data.startswith("adm:welcome_preview:"))
async def preview(call: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(bot_id)
    if config.welcome_photo_file_id:
        await call.message.answer_photo(config.welcome_photo_file_id, caption=config.welcome_caption or " ")
    else:
        await call.message.answer(config.welcome_caption or "(empty)")
    await call.answer()
