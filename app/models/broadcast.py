from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import BroadcastContentType, BroadcastJobStatus, BroadcastStatus


class Broadcast(Base, TimestampMixin):
    """A broadcast campaign definition for a single child bot."""

    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)

    content_type: Mapped[BroadcastContentType] = mapped_column(
        Enum(BroadcastContentType, name="broadcast_content_type"), nullable=False
    )
    media_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)  # Telegram HTML
    inline_buttons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # [[{text,url}], ...]

    status: Mapped[BroadcastStatus] = mapped_column(
        Enum(BroadcastStatus, name="broadcast_status"), default=BroadcastStatus.DRAFT, nullable=False
    )
    scheduled_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    jobs: Mapped[list["BroadcastJob"]] = relationship(back_populates="broadcast", cascade="all, delete-orphan")


class BroadcastJob(Base, TimestampMixin):
    """Per-recipient fan-out row, so a broadcast can be retried/resumed and
    per-user delivery failures (e.g. blocked bot) don't fail the whole batch.
    """

    __tablename__ = "broadcast_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[BroadcastJobStatus] = mapped_column(
        Enum(BroadcastJobStatus, name="broadcast_job_status"), default=BroadcastJobStatus.PENDING, nullable=False
    )
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    broadcast: Mapped["Broadcast"] = relationship(back_populates="jobs")
