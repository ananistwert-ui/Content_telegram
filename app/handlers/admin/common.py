from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.bot import Bot


def admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🤖 Manage Bots", callback_data="adm:bots")],
        [InlineKeyboardButton(text="📊 Statistics", callback_data="adm:stats")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bots_list_keyboard(bots: list[Bot]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{'🟢' if b.is_active else '🔴'} {b.display_name}", callback_data=f"adm:bot:{b.id}")]
        for b in bots
    ]
    rows.append([InlineKeyboardButton(text="➕ Register new bot", callback_data="adm:bot_register")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="adm:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bot_detail_keyboard(bot: Bot) -> InlineKeyboardMarkup:
    toggle_label = "🔴 Disable" if bot.is_active else "🟢 Enable"
    rows = [
        [InlineKeyboardButton(text="✏️ Welcome message", callback_data=f"adm:welcome:{bot.id}")],
        [InlineKeyboardButton(text="🔐 Captcha", callback_data=f"adm:captcha:{bot.id}")],
        [InlineKeyboardButton(text="📋 Menu buttons", callback_data=f"adm:menu:{bot.id}")],
        [InlineKeyboardButton(text="📡 Channels", callback_data=f"adm:channels:{bot.id}")],
        [InlineKeyboardButton(text="⭐ Private channels", callback_data=f"adm:pc:{bot.id}")],
        [InlineKeyboardButton(text=toggle_label, callback_data=f"adm:bot_toggle:{bot.id}")],
        [InlineKeyboardButton(text="⬅️ Back to bot list", callback_data="adm:bots")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def get_selected_bot_id(state: FSMContext) -> int | None:
    data = await state.get_data()
    return data.get("selected_bot_id")


async def set_selected_bot_id(state: FSMContext, bot_id: int) -> None:
    await state.update_data(selected_bot_id=bot_id)
