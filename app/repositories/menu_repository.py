from __future__ import annotations

from sqlalchemy import select

from app.models.menu import MenuButton
from app.repositories.base import BaseRepository


class MenuRepository(BaseRepository[MenuButton]):
    model = MenuButton

    async def list_for_bot(self, bot_id: int, visible_only: bool = True) -> list[MenuButton]:
        stmt = select(MenuButton).where(MenuButton.bot_id == bot_id)
        if visible_only:
            stmt = stmt.where(MenuButton.is_visible.is_(True))
        stmt = stmt.order_by(MenuButton.row, MenuButton.position)
        return list((await self.session.execute(stmt)).scalars().all())
