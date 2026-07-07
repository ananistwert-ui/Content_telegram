from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot as AiogramBot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel, PrivateChannel
from app.models.enums import AnalyticsEventType
from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.channel_repository import PrivateChannelRepository
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccessCheckResult:
    granted: bool
    missing_channels: list[Channel]


class PrivateChannelService:
    """Business rule: a user may access a PrivateChannel only if subscribed
    to ALL of its required Channels (news channel is always included by
    convention -- enforced when the admin attaches requirements, not
    hardcoded here, so it stays fully data-driven).
    """

    def __init__(self, session: AsyncSession, subscription_service: SubscriptionService) -> None:
        self.session = session
        self.subscription_service = subscription_service
        self.private_channels = PrivateChannelRepository(session)
        self.analytics = AnalyticsRepository(session)

    async def list_private_channels(self, bot_id: int) -> list[PrivateChannel]:
        return await self.private_channels.list_for_bot(bot_id)

    async def check_access(self, tg_user_id: int, private_channel: PrivateChannel) -> AccessCheckResult:
        required = [req.required_channel for req in private_channel.requirements]
        if not required:
            return AccessCheckResult(granted=True, missing_channels=[])

        statuses = await self.subscription_service.check_all(tg_user_id, required)
        missing = [ch for ch in required if not statuses[ch.id]]
        return AccessCheckResult(granted=not missing, missing_channels=missing)

    async def request_access(
        self, bot: AiogramBot, user: User, private_channel: PrivateChannel
    ) -> AccessCheckResult:
        """Called when the user presses a private-channel button. Logs the
        attempt, checks requirements, and -- if satisfied -- returns the
        invite link for the bot layer to send. Approval of the resulting
        ChatJoinRequest happens separately in `handle_join_request` once
        Telegram delivers that update.
        """
        await self.analytics.log(
            bot_id=private_channel.bot_id,
            user_id=user.id,
            event_type=AnalyticsEventType.PRIVATE_CHANNEL_REQUESTED,
            meta={"private_channel_id": private_channel.id},
        )
        result = await self.check_access(user.tg_id, private_channel)
        if not result.granted:
            await self.analytics.log(
                bot_id=private_channel.bot_id,
                user_id=user.id,
                event_type=AnalyticsEventType.PRIVATE_CHANNEL_BLOCKED,
                meta={
                    "private_channel_id": private_channel.id,
                    "missing": [c.id for c in result.missing_channels],
                },
            )
        return result

    async def handle_join_request(
        self, bot: AiogramBot, user: User, private_channel: PrivateChannel
    ) -> bool:
        """Invoked from the ChatJoinRequest update handler. Re-validates
        requirements at the moment of the actual join request (state may
        have changed since the user got the invite link) and approves or
        declines accordingly. This is the authoritative gate -- the invite
        link itself grants nothing without this approval.
        """
        from app.models.analytics import JoinEvent

        result = await self.check_access(user.tg_id, private_channel)
        chat_id = private_channel.channel.tg_chat_id
        try:
            if result.granted:
                await bot.approve_chat_join_request(chat_id=chat_id, user_id=user.tg_id)
                event_type = AnalyticsEventType.JOIN_REQUEST_APPROVED
            else:
                await bot.decline_chat_join_request(chat_id=chat_id, user_id=user.tg_id)
                event_type = AnalyticsEventType.JOIN_REQUEST_DECLINED
        except TelegramAPIError as exc:
            logger.error("Failed to resolve join request for user=%s chat=%s: %s", user.tg_id, chat_id, exc)
            return False

        self.session.add(
            JoinEvent(
                user_id=user.id,
                private_channel_id=private_channel.id,
                approved=result.granted,
                reason=None if result.granted else "missing_requirements",
            )
        )
        await self.analytics.log(
            bot_id=private_channel.bot_id,
            user_id=user.id,
            event_type=event_type,
            meta={"private_channel_id": private_channel.id},
        )
        return result.granted
