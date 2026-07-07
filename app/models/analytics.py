from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AnalyticsEventType


class UserSubscription(Base, TimestampMixin):
    """Persisted result of the last subscription check for a (user, channel)
    pair. Redis holds the short-TTL hot cache used during a single
    "Check Again" flow; this table is the durable record analytics query.
    """

    __tablename__ = "user_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    checked_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class JoinEvent(Base, TimestampMixin):
    """Audit trail of every join-request decision for a private channel."""

    __tablename__ = "join_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    private_channel_id: Mapped[int] = mapped_column(
        ForeignKey("private_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(nullable=True)


class AnalyticsEvent(Base, TimestampMixin):
    """Generic, append-only event log. Deliberately schema-light (JSON
    `meta`) so new metrics never require a migration -- aggregation
    happens in queries/materialized views, not in table structure.
    """

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[AnalyticsEventType] = mapped_column(
        Enum(AnalyticsEventType, name="analytics_event_type"), nullable=False, index=True
    )
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
