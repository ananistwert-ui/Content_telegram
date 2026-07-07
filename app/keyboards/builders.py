from __future__ import annotations

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.bot import BotConfig
from app.models.channel import Channel, PrivateChannel
from app.models.enums import ButtonType
from app.models.menu import MenuButton


def build_captcha_keyboard(config: BotConfig, options: list[str]) -> InlineKeyboardMarkup:
    """2-per-row emoji grid, callback_data carries the chosen emoji."""
    buttons = [InlineKeyboardButton(text=emoji, callback_data=f"captcha:{emoji}") for emoji in options]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_main_menu_keyboard(buttons: list[MenuButton]) -> InlineKeyboardMarkup:
    """Renders the admin-configured menu. Rows are grouped by `row`, then
    ordered by `position` within the row -- this is how the admin controls
    "button order" and multi-per-row layouts without extra tables.
    """
    rows_map: dict[int, list[InlineKeyboardButton]] = {}
    for btn in buttons:
        kb_button = _render_menu_button(btn)
        rows_map.setdefault(btn.row, []).append(kb_button)

    ordered_rows = [rows_map[row] for row in sorted(rows_map.keys())]
    return InlineKeyboardMarkup(inline_keyboard=ordered_rows)


def _render_menu_button(btn: MenuButton) -> InlineKeyboardButton:
    if btn.type == ButtonType.URL:
        return InlineKeyboardButton(text=btn.text, url=btn.payload["url"])
    if btn.type == ButtonType.EXTERNAL_CHAT:
        username = btn.payload["username"].lstrip("@")
        prefilled = btn.payload.get("prefilled_text", "")
        url = f"https://t.me/{username}"
        if prefilled:
            url += f"?text={quote(prefilled)}"
        return InlineKeyboardButton(text=btn.text, url=url)
    # CALLBACK
    action = btn.payload.get("action", "noop")
    return InlineKeyboardButton(text=btn.text, callback_data=f"menu:{action}:{btn.id}")


def build_missing_requirements_keyboard(missing: list[Channel], recheck_callback: str) -> InlineKeyboardMarkup:
    rows = []
    for channel in missing:
        if channel.url:
            rows.append([InlineKeyboardButton(text=channel.label, url=channel.url)])
    rows.append([InlineKeyboardButton(text="🔄 Check Again", callback_data=recheck_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_private_channels_keyboard(private_channels: list[PrivateChannel]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=pc.title, callback_data=f"private_channel:{pc.id}")]
        for pc in private_channels
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_join_link_keyboard(invite_link: str, title: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"➡️ Join {title}", url=invite_link)]])
