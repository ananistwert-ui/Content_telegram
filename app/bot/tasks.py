from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.db.session import AsyncSessionFactory
from app.repositories.broadcast_repository import BroadcastRepository
from app.repositories.bot_repository import BotRepository
from app.services.broadcast_service import BroadcastService

logger = logging.getLogger(__name__)


async def send_broadcast_task(ctx: dict, broadcast_id: int) -> None:
    """arq job: fans out one broadcast. Enqueued either immediately
    ("send now") or by the cron sweep once its scheduled_at arrives.
    """
    async with AsyncSessionFactory() as session:
        broadcasts = BroadcastRepository(session)
        bots = BotRepository(session)

        broadcast = await broadcasts.get(broadcast_id)
        if broadcast is None:
            logger.error("send_broadcast_task: broadcast %s not found", broadcast_id)
            return

        db_bot = await bots.get(broadcast.bot_id)
        bot = Bot(token=db_bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            service = BroadcastService(session)
            sent, failed = await service.send_now(bot, broadcast)
            await session.commit()
            logger.info("Broadcast %s done: sent=%s failed=%s", broadcast_id, sent, failed)
        finally:
            await bot.session.close()


async def sweep_scheduled_broadcasts(ctx: dict) -> None:
    """arq cron job (runs every minute): finds broadcasts whose
    scheduled_at has arrived and enqueues them for sending. Kept separate
    from send_broadcast_task so retries/backoff apply per-broadcast.
    """
    import datetime as dt

    from arq import ArqRedis

    async with AsyncSessionFactory() as session:
        broadcasts = BroadcastRepository(session)
        due = await broadcasts.list_due(dt.datetime.now(dt.timezone.utc))
        redis: ArqRedis = ctx["redis"]
        for broadcast in due:
            await redis.enqueue_job("send_broadcast_task", broadcast.id)
            logger.info("Enqueued scheduled broadcast %s", broadcast.id)
