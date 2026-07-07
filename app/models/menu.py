from __future__ import annotations

from sqlalchemy import Boolean, Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ButtonType


class MenuButton(Base, TimestampMixin):
    """A single inline-keyboard button on a child bot's main menu.

    `payload` holds type-specific data so we don't need a wide sparse
    table:
      - URL:            {"url": "https://t.me/news_channel"}
      - EXTERNAL_CHAT:  {"username": "someone", "prefilled_text": "Hello"}
      - CALLBACK:       {"action": "subscribe" | "open_private_channels" | ...}
    """

    __tablename__ = "menu_buttons"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)

    text: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[ButtonType] = mapped_column(Enum(ButtonType, name="button_type"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    position: Mapped[int] = mapped_column(default=0, nullable=False)
    row: Mapped[int] = mapped_column(default=0, nullable=False)  # allows 2-per-row layouts etc.
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bot: Mapped["Bot"] = relationship(back_populates="menu_buttons")  # noqa: F821
