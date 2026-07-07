from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """An end-user as seen by a specific child bot.

    The same human interacting with two different child bots produces two
    rows here -- this is intentional: it is what makes per-bot lead
    attribution and analytics trivial (bot_id is always present).
    """

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("bot_id", "tg_id", name="uq_users_bot_tg"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    captcha_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    captcha_attempts: Mapped[int] = mapped_column(default=0, nullable=False)

    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_blocked_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
