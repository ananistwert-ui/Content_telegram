from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from app.bot.tasks import send_broadcast_task, sweep_scheduled_broadcasts
from app.core.config import settings


class WorkerSettings:
    """Run with: `arq app.bot.worker_settings.WorkerSettings`"""

    functions = [send_broadcast_task]
    cron_jobs = [cron(sweep_scheduled_broadcasts, minute=set(range(60)), run_at_startup=True)]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_DSN)
    max_jobs = 10
