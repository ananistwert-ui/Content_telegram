from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bot import Bot, BotConfig
from app.repositories.base import BaseRepository


class BotRepository(BaseRepository[Bot]):
    model = Bot

    async def get_with_config(self, bot_id: int) -> Bot | None:
        stmt = select(Bot).where(Bot.id == bot_id).options(selectinload(Bot.config))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_active_child_bots(self) -> list[Bot]:
        stmt = select(Bot).where(Bot.is_active.is_(True), Bot.is_master.is_(False)).options(selectinload(Bot.config))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_token(self, token: str) -> Bot | None:
        stmt = select(Bot).where(Bot.token == token).options(selectinload(Bot.config))
        return (await self.session.execute(stmt)).scalar_one_or_none()


class BotConfigRepository(BaseRepository[BotConfig]):
    model = BotConfig

    async def get_by_bot_id(self, bot_id: int) -> BotConfig | None:
        stmt = select(BotConfig).where(BotConfig.bot_id == bot_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()
