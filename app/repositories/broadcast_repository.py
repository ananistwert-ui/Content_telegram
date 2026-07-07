from __future__ import annotations

import datetime as dt

<<<<<<< HEAD
from sqlalchemy import select
=======
from sqlalchemy import select, func
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)

from app.models.broadcast import Broadcast, BroadcastJob
from app.models.enums import BroadcastJobStatus, BroadcastStatus
from app.repositories.base import BaseRepository


class BroadcastRepository(BaseRepository[Broadcast]):
    model = Broadcast

    async def list_due(self, now: dt.datetime) -> list[Broadcast]:
        stmt = select(Broadcast).where(
<<<<<<< HEAD
            # Исправление: добавляем .value
            Broadcast.status == BroadcastStatus.SCHEDULED.value,
            Broadcast.scheduled_at <= now,
        )
        return list((await self.session.execute(stmt)).scalars().all())
=======
            Broadcast.status == BroadcastStatus.SCHEDULED.value,
            Broadcast.scheduled_at <= now,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)


class BroadcastJobRepository(BaseRepository[BroadcastJob]):
    model = BroadcastJob

    async def list_pending(self, broadcast_id: int, limit: int = 500) -> list[BroadcastJob]:
        stmt = (
            select(BroadcastJob)
            .where(
                BroadcastJob.broadcast_id == broadcast_id, 
<<<<<<< HEAD
                # Исправление: добавляем .value
=======
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
                BroadcastJob.status == BroadcastJobStatus.PENDING.value
            )
            .limit(limit)
        )
<<<<<<< HEAD
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_status(self, broadcast_id: int, status: BroadcastJobStatus) -> int:
        from sqlalchemy import func

=======
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(self, broadcast_id: int, status: BroadcastJobStatus) -> int:
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
        stmt = (
            select(func.count())
            .select_from(BroadcastJob)
            .where(
                BroadcastJob.broadcast_id == broadcast_id, 
<<<<<<< HEAD
                # Исправление: добавляем .value, так как status передается как Enum
                BroadcastJob.status == status.value
            )
        )
        return (await self.session.execute(stmt)).scalar_one()ы
=======
                BroadcastJob.status == status.value
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
>>>>>>> 4c2f3e7 (fix: resolve Enum/Postgres type errors, fix logger context, fix webhook startup sequence)
