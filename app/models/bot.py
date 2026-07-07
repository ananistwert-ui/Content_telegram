from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Bot(Base, TimestampMixin):
    """A registered Telegram bot instance (master admin bot or a child bot)."""

    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    config: Mapped["BotConfig"] = relationship(back_populates="bot", uselist=False, cascade="all, delete-orphan")
    channels: Mapped[list["Channel"]] = relationship(back_populates="bot", cascade="all, delete-orphan")  # noqa: F821
    menu_buttons: Mapped[list["MenuButton"]] = relationship(back_populates="bot", cascade="all, delete-orphan")  # noqa: F821


class BotConfig(Base, TimestampMixin):
    """Per-bot branding, welcome message, and captcha configuration.

    Kept as a 1:1 side table (rather than columns on Bot) so it can be
    edited/replaced independently and so `Bot` stays a lean identity row.
    """

    __tablename__ = "bot_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Branding
    brand_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_branding: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Welcome message
    welcome_photo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    welcome_caption: Mapped[str | None] = mapped_column(Text, nullable=True)  # stored as Telegram HTML

    # Captcha
    captcha_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    captcha_caption: Mapped[str] = mapped_column(Text, default="Select {emoji}", nullable=False)
    captcha_photo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    captcha_emojis: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["🍎", "🍌", "🍉", "🍇"], nullable=False)
    captcha_correct_emoji: Mapped[str] = mapped_column(String(8), default="🍎", nullable=False)

    bot: Mapped["Bot"] = relationship(back_populates="config")
