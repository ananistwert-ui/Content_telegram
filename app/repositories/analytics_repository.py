from __future__ import annotations

from sqlalchemy import func, select

from app.models.analytics import AnalyticsEvent, JoinEvent
from app.models.channel import PrivateChannel
from app.models.enums import AnalyticsEventType
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[AnalyticsEvent]):
    model = AnalyticsEvent

    async def log(self, bot_id: int, event_type: AnalyticsEventType, user_id: int | None = None, meta: dict | None = None) -> None:
        self.add(AnalyticsEvent(bot_id=bot_id, user_id=user_id, event_type=event_type, meta=meta or {}))
        await self.flush()

    async def count_event(self, bot_id: int, event_type: AnalyticsEventType) -> int:
        stmt = (
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.bot_id == bot_id, AnalyticsEvent.event_type == event_type)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def leads_per_bot(self) -> list[tuple[int, int]]:
        """Returns [(bot_id, count_of_bot_started_events), ...] for the
        cross-bot comparison dashboard.
        """
        stmt = (
            select(AnalyticsEvent.bot_id, func.count())
            .where(AnalyticsEvent.event_type == AnalyticsEventType.BOT_STARTED)
            .group_by(AnalyticsEvent.bot_id)
        )
        return [(row[0], row[1]) for row in (await self.session.execute(stmt)).all()]

    async def count_joins_for_bot(self, bot_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(JoinEvent)
            .join(PrivateChannel, PrivateChannel.id == JoinEvent.private_channel_id)
            .where(JoinEvent.approved.is_(True), PrivateChannel.bot_id == bot_id)
        )
        return (await self.session.execute(stmt)).scalar_one()
