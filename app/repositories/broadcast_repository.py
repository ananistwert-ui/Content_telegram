from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app.models.broadcast import Broadcast, BroadcastJob
from app.models.enums import BroadcastJobStatus, BroadcastStatus
from app.repositories.base import BaseRepository


class BroadcastRepository(BaseRepository[Broadcast]):
    model = Broadcast

    async def list_due(self, now: dt.datetime) -> list[Broadcast]:
        stmt = select(Broadcast).where(
            # Исправление: добавляем .value
            Broadcast.status == BroadcastStatus.SCHEDULED.value,
            Broadcast.scheduled_at <= now,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class BroadcastJobRepository(BaseRepository[BroadcastJob]):
    model = BroadcastJob

    async def list_pending(self, broadcast_id: int, limit: int = 500) -> list[BroadcastJob]:
        stmt = (
            select(BroadcastJob)
            .where(
                BroadcastJob.broadcast_id == broadcast_id, 
                # Исправление: добавляем .value
                BroadcastJob.status == BroadcastJobStatus.PENDING.value
            )
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_status(self, broadcast_id: int, status: BroadcastJobStatus) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(BroadcastJob)
            .where(
                BroadcastJob.broadcast_id == broadcast_id, 
                # Исправление: добавляем .value, так как status передается как Enum
                BroadcastJob.status == status.value
            )
        )
        return (await self.session.execute(stmt)).scalar_one()ы