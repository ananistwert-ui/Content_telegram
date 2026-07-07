from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.broadcast import Broadcast, BroadcastJob
from app.models.enums import BroadcastContentType, BroadcastJobStatus, BroadcastStatus
from app.repositories.broadcast_repository import BroadcastJobRepository, BroadcastRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


def _build_inline_keyboard(inline_buttons: list[list[dict]]) -> InlineKeyboardMarkup | None:
    if not inline_buttons:
        return None
    rows = [[InlineKeyboardButton(text=b["text"], url=b["url"]) for b in row] for row in inline_buttons]
    return InlineKeyboardMarkup(inline_keyboard=rows)


class BroadcastService:
    """Creates per-recipient BroadcastJob rows (so a crash mid-send can be
    resumed) and fans them out at a bounded rate to stay under Telegram's
    ~30 msg/sec global cap. Each user's failure (blocked bot, deactivated
    account) is recorded on their own job row and does not affect the rest
    of the batch.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.broadcasts = BroadcastRepository(session)
        self.jobs = BroadcastJobRepository(session)
        self.users = UserRepository(session)

    async def create_jobs(self, broadcast: Broadcast) -> int:
        recipients = await self.users.list_recipients_for_broadcast(broadcast.bot_id)
        for user in recipients:
            self.jobs.add(BroadcastJob(broadcast_id=broadcast.id, user_id=user.id))
        await self.jobs.flush()
        return len(recipients)

    async def send_now(self, bot: Bot, broadcast: Broadcast) -> tuple[int, int]:
        """Sends all PENDING jobs for this broadcast. Returns (sent, failed).
        Safe to call repeatedly -- already-SENT/FAILED jobs are skipped, so
        this doubles as the retry/resume mechanism.
        """
        broadcast.status = BroadcastStatus.SENDING
        await self.session.flush()

        keyboard = _build_inline_keyboard(broadcast.inline_buttons)
        sent, failed = 0, 0
        delay = 1.0 / max(settings.BROADCAST_MESSAGES_PER_SECOND, 1)

        while True:
            batch = await self.jobs.list_pending(broadcast.id, limit=200)
            if not batch:
                break
            for job in batch:
                user = await self.users.get(job.user_id)
                try:
                    await self._send_one(bot, broadcast, user.tg_id, keyboard)
                    job.status = BroadcastJobStatus.SENT
                    sent += 1
                except TelegramForbiddenError:
                    job.status = BroadcastJobStatus.SKIPPED
                    job.error = "blocked_bot"
                    user.is_blocked_bot = True
                    failed += 1
                except TelegramRetryAfter as exc:
                    logger.warning("Rate limited, sleeping %s s", exc.retry_after)
                    await asyncio.sleep(exc.retry_after)
                    continue  # retry this job on next loop pass (still PENDING)
                except Exception as exc:  # noqa: BLE001
                    job.status = BroadcastJobStatus.FAILED
                    job.error = str(exc)[:500]
                    failed += 1
                await asyncio.sleep(delay)
            await self.session.flush()

        broadcast.status = BroadcastStatus.SENT
        await self.session.flush()
        return sent, failed

    async def _send_one(self, bot: Bot, broadcast: Broadcast, chat_id: int, keyboard: InlineKeyboardMarkup | None) -> None:
        if broadcast.content_type == BroadcastContentType.TEXT:
            await bot.send_message(chat_id, broadcast.caption or "", reply_markup=keyboard)
        elif broadcast.content_type == BroadcastContentType.PHOTO:
            await bot.send_photo(chat_id, broadcast.media_file_id, caption=broadcast.caption, reply_markup=keyboard)
        elif broadcast.content_type == BroadcastContentType.VIDEO:
            await bot.send_video(chat_id, broadcast.media_file_id, caption=broadcast.caption, reply_markup=keyboard)
        elif broadcast.content_type == BroadcastContentType.GIF:
            await bot.send_animation(chat_id, broadcast.media_file_id, caption=broadcast.caption, reply_markup=keyboard)
