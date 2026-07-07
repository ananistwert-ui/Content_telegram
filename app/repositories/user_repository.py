from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_tg_id(self, bot_id: int, tg_id: int) -> User | None:
        stmt = select(User).where(User.bot_id == bot_id, User.tg_id == tg_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_or_create(self, bot_id: int, tg_id: int, username: str | None, full_name: str | None) -> User:
        user = await self.get_by_tg_id(bot_id, tg_id)
        if user is None:
            user = User(
                bot_id=bot_id,
                tg_id=tg_id,
                username=username,
                full_name=full_name,
                last_seen_at=dt.datetime.now(dt.timezone.utc),
            )
            self.add(user)
            await self.flush()
        else:
            user.username = username
            user.full_name = full_name
            user.last_seen_at = dt.datetime.now(dt.timezone.utc)
        return user

    async def count_total(self, bot_id: int) -> int:
        stmt = select(func.count()).select_from(User).where(User.bot_id == bot_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_captcha_passed(self, bot_id: int) -> int:
        stmt = select(func.count()).select_from(User).where(User.bot_id == bot_id, User.captcha_passed.is_(True))
        return (await self.session.execute(stmt)).scalar_one()

    async def count_active_since(self, bot_id: int, since: dt.datetime) -> int:
        stmt = select(func.count()).select_from(User).where(User.bot_id == bot_id, User.last_seen_at >= since)
        return (await self.session.execute(stmt)).scalar_one()

    async def list_recipients_for_broadcast(self, bot_id: int) -> list[User]:
        stmt = select(User).where(User.bot_id == bot_id, User.is_blocked_bot.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())
