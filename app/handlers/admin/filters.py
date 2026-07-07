from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.core.config import settings


class IsAdminFilter(BaseFilter):
    """Single hard-coded admin id, per spec (no multi-admin roles)."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and user.id == settings.ADMIN_TG_ID)
