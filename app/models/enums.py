from __future__ import annotations

import enum


class ChannelType(str, enum.Enum):
    NEWS = "news"
    REQUIRED = "required"        # generic sponsor/required-subscription channel
    FORUM = "forum"
    PRIVATE = "private"          # the gated destination channel itself


class ButtonType(str, enum.Enum):
    URL = "url"
    CALLBACK = "callback"
    EXTERNAL_CHAT = "external_chat"


class BroadcastContentType(str, enum.Enum):
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    GIF = "gif"


class BroadcastStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BroadcastJobStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"  # e.g. user blocked the bot


class AnalyticsEventType(str, enum.Enum):
    BOT_STARTED = "bot_started"
    CAPTCHA_SHOWN = "captcha_shown"
    CAPTCHA_PASSED = "captcha_passed"
    CAPTCHA_FAILED = "captcha_failed"
    MENU_SHOWN = "menu_shown"
    PRIVATE_CHANNEL_REQUESTED = "private_channel_requested"
    PRIVATE_CHANNEL_BLOCKED = "private_channel_blocked"
    JOIN_REQUEST_RECEIVED = "join_request_received"
    JOIN_REQUEST_APPROVED = "join_request_approved"
    JOIN_REQUEST_DECLINED = "join_request_declined"
