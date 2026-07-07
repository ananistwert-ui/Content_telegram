"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-07 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    channel_type = sa.Enum("news", "required", "forum", "private", name="channel_type")
    button_type = sa.Enum("url", "callback", "external_chat", name="button_type")
    broadcast_content_type = sa.Enum("text", "photo", "video", "gif", name="broadcast_content_type")
    broadcast_status = sa.Enum("draft", "scheduled", "sending", "sent", "failed", "cancelled", name="broadcast_status")
    broadcast_job_status = sa.Enum("pending", "sent", "failed", "skipped", name="broadcast_job_status")
    analytics_event_type = sa.Enum(
        "bot_started", "captcha_shown", "captcha_passed", "captcha_failed", "menu_shown",
        "private_channel_requested", "private_channel_blocked", "join_request_received",
        "join_request_approved", "join_request_declined", name="analytics_event_type",
    )

    op.create_table(
        "bots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("is_master", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "bot_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("brand_name", sa.String(128), nullable=True),
        sa.Column("extra_branding", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("welcome_photo_file_id", sa.String(256), nullable=True),
        sa.Column("welcome_caption", sa.Text(), nullable=True),
        sa.Column("captcha_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("captcha_caption", sa.Text(), nullable=False, server_default="Select {emoji}"),
        sa.Column("captcha_photo_file_id", sa.String(256), nullable=True),
        sa.Column("captcha_emojis", sa.JSON(), nullable=False),
        sa.Column("captcha_correct_emoji", sa.String(8), nullable=False, server_default="🍎"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tg_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("full_name", sa.String(256), nullable=True),
        sa.Column("captcha_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("captcha_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_blocked_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("bot_id", "tg_id", name="uq_users_bot_tg"),
    )
    op.create_index("ix_users_bot_id", "users", ["bot_id"])
    op.create_index("ix_users_tg_id", "users", ["tg_id"])

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", channel_type, nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("tg_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("url", sa.String(256), nullable=True),
        sa.Column("is_bot_admin_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("bot_id", "tg_chat_id", name="uq_channels_bot_chat"),
    )
    op.create_index("ix_channels_bot_id", "channels", ["bot_id"])

    op.create_table(
        "private_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("invite_link", sa.String(256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_private_channels_bot_id", "private_channels", ["bot_id"])

    op.create_table(
        "channel_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("private_channel_id", sa.Integer(), sa.ForeignKey("private_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("required_channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("private_channel_id", "required_channel_id", name="uq_requirement_pair"),
    )
    op.create_index("ix_channel_requirements_private_channel_id", "channel_requirements", ["private_channel_id"])
    op.create_index("ix_channel_requirements_required_channel_id", "channel_requirements", ["required_channel_id"])

    op.create_table(
        "menu_buttons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.String(64), nullable=False),
        sa.Column("type", button_type, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("row", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_menu_buttons_bot_id", "menu_buttons", ["bot_id"])

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_type", broadcast_content_type, nullable=False),
        sa.Column("media_file_id", sa.String(256), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("inline_buttons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", broadcast_status, nullable=False, server_default="draft"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_broadcasts_bot_id", "broadcasts", ["bot_id"])

    op.create_table(
        "broadcast_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("broadcast_id", sa.Integer(), sa.ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", broadcast_job_status, nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_broadcast_jobs_broadcast_id", "broadcast_jobs", ["broadcast_id"])
    op.create_index("ix_broadcast_jobs_user_id", "broadcast_jobs", ["user_id"])

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_subscribed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])
    op.create_index("ix_user_subscriptions_channel_id", "user_subscriptions", ["channel_id"])

    op.create_table(
        "join_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("private_channel_id", sa.Integer(), sa.ForeignKey("private_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_join_events_user_id", "join_events", ["user_id"])
    op.create_index("ix_join_events_private_channel_id", "join_events", ["private_channel_id"])

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", analytics_event_type, nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analytics_events_bot_id", "analytics_events", ["bot_id"])
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"])
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_table("join_events")
    op.drop_table("user_subscriptions")
    op.drop_table("broadcast_jobs")
    op.drop_table("broadcasts")
    op.drop_table("menu_buttons")
    op.drop_table("channel_requirements")
    op.drop_table("private_channels")
    op.drop_table("channels")
    op.drop_table("users")
    op.drop_table("bot_configs")
    op.drop_table("bots")

    sa.Enum(name="analytics_event_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="broadcast_job_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="broadcast_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="broadcast_content_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="button_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="channel_type").drop(op.get_bind(), checkfirst=True)
