from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.admin.filters import IsAdminFilter
from app.handlers.admin.states import CaptchaEditStates
from app.keyboards.builders import build_captcha_keyboard
from app.repositories.bot_repository import BotConfigRepository

router = Router(name="admin_captcha")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


def _captcha_menu_keyboard(bot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Caption", callback_data=f"adm:captcha_caption:{bot_id}")],
            [InlineKeyboardButton(text="🖼 Photo", callback_data=f"adm:captcha_photo:{bot_id}")],
            [InlineKeyboardButton(text="🍎 Emoji options", callback_data=f"adm:captcha_emojis:{bot_id}")],
            [InlineKeyboardButton(text="✅ Correct emoji", callback_data=f"adm:captcha_correct:{bot_id}")],
            [InlineKeyboardButton(text="👁 Preview", callback_data=f"adm:captcha_preview:{bot_id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"adm:bot:{bot_id}")],
        ]
    )


@router.callback_query(lambda c: c.data and c.data.startswith("adm:captcha:"))
async def captcha_menu(call: CallbackQuery) -> None:
    bot_id = int(call.data.split(":")[-1])
    await call.message.edit_text("🔐 <b>Captcha settings</b>", reply_markup=_captcha_menu_keyboard(bot_id))
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:captcha_caption:"))
async def ask_caption(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(CaptchaEditStates.waiting_caption)
    await call.message.edit_text(
        "Send the new captcha caption (HTML formatting supported). "
        "Use <code>{emoji}</code> as a placeholder for the correct emoji, e.g. \"Select {emoji}\"."
    )
    await call.answer()


@router.message(CaptchaEditStates.waiting_caption)
async def receive_caption(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(data["target_bot_id"])
    config.captcha_caption = message.html_text
    await state.clear()
    await message.answer("✅ Captcha caption updated.")


@router.callback_query(lambda c: c.data and c.data.startswith("adm:captcha_photo:"))
async def ask_photo(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(CaptchaEditStates.waiting_photo)
    await call.message.edit_text("Send the new captcha photo (or /skip to remove it and use text-only captcha).")
    await call.answer()


@router.message(CaptchaEditStates.waiting_photo, lambda m: m.text == "/skip")
async def skip_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(data["target_bot_id"])
    config.captcha_photo_file_id = None
    await state.clear()
    await message.answer("✅ Captcha photo removed.")


@router.message(CaptchaEditStates.waiting_photo)
async def receive_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.photo:
        await message.answer("Please send a photo, or /skip.")
        return
    data = await state.get_data()
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(data["target_bot_id"])
    config.captcha_photo_file_id = message.photo[-1].file_id
    await state.clear()
    await message.answer("✅ Captcha photo updated.")


@router.callback_query(lambda c: c.data and c.data.startswith("adm:captcha_emojis:"))
async def ask_emojis(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(call.data.split(":")[-1])
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(CaptchaEditStates.waiting_emojis)
    await call.message.edit_text("Send the emoji options separated by spaces, e.g.: 🍎 🍌 🍉 🍇")
    await call.answer()


@router.message(CaptchaEditStates.waiting_emojis)
async def receive_emojis(message: Message, state: FSMContext, session: AsyncSession) -> None:
    emojis = message.text.split()
    if len(emojis) < 2:
        await message.answer("Please send at least 2 emojis, separated by spaces.")
        return
    data = await state.get_data()
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(data["target_bot_id"])
    config.captcha_emojis = emojis
    if config.captcha_correct_emoji not in emojis:
        config.captcha_correct_emoji = emojis[0]
    await state.clear()
    await message.answer(f"✅ Emoji options updated: {' '.join(emojis)}\nCorrect emoji is now: {config.captcha_correct_emoji}")


@router.callback_query(lambda c: c.data and c.data.startswith("adm:captcha_correct:"))
async def ask_correct(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(bot_id)
    await state.update_data(target_bot_id=bot_id)
    await state.set_state(CaptchaEditStates.waiting_correct_emoji)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=e, callback_data=f"adm:set_correct:{e}") for e in config.captcha_emojis]]
    )
    await call.message.edit_text("Pick the correct emoji:", reply_markup=keyboard)
    await call.answer()


@router.callback_query(CaptchaEditStates.waiting_correct_emoji, lambda c: c.data and c.data.startswith("adm:set_correct:"))
async def set_correct(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    emoji = call.data.split(":")[-1]
    data = await state.get_data()
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(data["target_bot_id"])
    config.captcha_correct_emoji = emoji
    await state.clear()
    await call.message.edit_text(f"✅ Correct emoji set to {emoji}")
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("adm:captcha_preview:"))
async def preview(call: CallbackQuery, session: AsyncSession) -> None:
    bot_id = int(call.data.split(":")[-1])
    repo = BotConfigRepository(session)
    config = await repo.get_by_bot_id(bot_id)
    keyboard = build_captcha_keyboard(config, config.captcha_emojis)
    if config.captcha_photo_file_id:
        await call.message.answer_photo(config.captcha_photo_file_id, caption=config.captcha_caption, reply_markup=keyboard)
    else:
        await call.message.answer(config.captcha_caption, reply_markup=keyboard)
    await call.answer()
