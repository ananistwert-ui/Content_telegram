from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class RegisterBotStates(StatesGroup):
    waiting_token = State()
    waiting_display_name = State()


class WelcomeEditStates(StatesGroup):
    waiting_photo = State()
    waiting_caption = State()


class CaptchaEditStates(StatesGroup):
    waiting_caption = State()
    waiting_photo = State()
    waiting_emojis = State()
    waiting_correct_emoji = State()


class MenuButtonStates(StatesGroup):
    waiting_text = State()
    waiting_type = State()
    waiting_url = State()
    waiting_external_username = State()
    waiting_external_prefilled = State()
    waiting_row_position = State()


class ChannelStates(StatesGroup):
    waiting_type = State()
    waiting_label = State()
    waiting_chat_id = State()
    waiting_url = State()


class PrivateChannelStates(StatesGroup):
    waiting_title = State()
    waiting_channel_pick = State()
    waiting_invite_link = State()
    waiting_requirement_pick = State()


class BroadcastStates(StatesGroup):
    waiting_content = State()
    waiting_caption = State()
    waiting_buttons = State()
    waiting_schedule_choice = State()
    waiting_schedule_datetime = State()
    waiting_confirmation = State()
