from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ChannelType


class Channel(Base, TimestampMixin):
    """Any Telegram channel/group/forum the bot needs to know about:
    news channel, sponsor/required channel, forum, or the private
    destination channel itself. `tg_chat_id` is only required for types
    the bot must call the Telegram API against (required/forum/private);
    a pure link-only announcement channel can omit it and rely on `url`.
    """

    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("bot_id", "tg_chat_id", name="uq_channels_bot_chat"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)

    type: Mapped[ChannelType] = mapped_column(Enum(ChannelType, name="channel_type"), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    tg_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_bot_admin_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bot: Mapped["Bot"] = relationship(back_populates="channels")  # noqa: F821
    private_channel: Mapped["PrivateChannel | None"] = relationship(
        back_populates="channel", uselist=False, cascade="all, delete-orphan"
    )


class PrivateChannel(Base, TimestampMixin):
    """A gated destination (VIP Silver, VIP Gold, ...). Wraps a Channel of
    type PRIVATE and adds the join-request invite link plus its list of
    required channels (via ChannelRequirement).
    """

    __tablename__ = "private_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    invite_link: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    channel: Mapped["Channel"] = relationship(back_populates="private_channel")
    requirements: Mapped[list["ChannelRequirement"]] = relationship(
        back_populates="private_channel", cascade="all, delete-orphan"
    )


class ChannelRequirement(Base, TimestampMixin):
    """Join table: which Channel rows are required to unlock a PrivateChannel."""

    __tablename__ = "channel_requirements"
    __table_args__ = (
        UniqueConstraint("private_channel_id", "required_channel_id", name="uq_requirement_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    private_channel_id: Mapped[int] = mapped_column(
        ForeignKey("private_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )

    private_channel: Mapped["PrivateChannel"] = relationship(back_populates="requirements")
    required_channel: Mapped["Channel"] = relationship(foreign_keys=[required_channel_id])
