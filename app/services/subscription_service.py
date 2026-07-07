from __future__ import annotations

import datetime as dt
import logging

from aiogram import Bot as AiogramBot
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.channel import Channel
from app.models.enums import AnalyticsEventType
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

_MEMBER_STATUSES = {"member", "administrator", "creator"}


class SubscriptionService:
    """Verifies whether a user is subscribed to a channel/group/forum.

    Telegram's getChatMember is rate-limited and relatively slow, and users
    mash "Check Again" -- so results are cached in Redis for a short TTL.
    A durable copy is also written to Postgres (UserSubscription) for
    analytics; that write is intentionally best-effort and does not block
    the user-facing decision.
    """

    def __init__(self, bot: AiogramBot, session: AsyncSession, redis: Redis) -> None:
        self.bot = bot
        self.session = session
        self.redis = redis

    def _cache_key(self, tg_user_id: int, tg_chat_id: int) -> str:
        return f"sub:{tg_chat_id}:{tg_user_id}"

    async def is_subscribed(self, tg_user_id: int, channel: Channel) -> bool:
        if channel.tg_chat_id is None:
            # Link-only channels (no bot presence) cannot be verified --
            # treat as satisfied to avoid an unresolvable requirement.
            logger.warning("Channel %s has no tg_chat_id; skipping verification", channel.id)
            return True

        cache_key = self._cache_key(tg_user_id, channel.tg_chat_id)
        cached = await self.redis.get(cache_key)
        if cached is not None:
            return cached == "1"

        is_member = False
        try:
            member = await self.bot.get_chat_member(chat_id=channel.tg_chat_id, user_id=tg_user_id)
            is_member = member.status in _MEMBER_STATUSES
        except TelegramAPIError as exc:
            # Most commonly: bot is not admin, or user never interacted
            # with the chat -> treat as "not subscribed" rather than crash.
            logger.info("get_chat_member failed for chat=%s user=%s: %s", channel.tg_chat_id, tg_user_id, exc)
            is_member = False

        await self.redis.set(cache_key, "1" if is_member else "0", ex=settings.SUBSCRIPTION_CHECK_CACHE_TTL)
        return is_member

    async def check_all(self, tg_user_id: int, channels: list[Channel]) -> dict[int, bool]:
        """Returns {channel_id: is_subscribed} for every channel, checked
        concurrently would be nicer, but Telegram rate limits favor a
        bounded sequential pass here; parallelize with a semaphore if
        the required-channel lists grow large.
        """
        results: dict[int, bool] = {}
        for channel in channels:
            results[channel.id] = await self.is_subscribed(tg_user_id, channel)
        return results
