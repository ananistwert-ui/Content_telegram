from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import ChatJoinRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.models.bot import Bot as BotModel
from app.models.enums import AnalyticsEventType
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.channel_repository import PrivateChannelRepository
from app.repositories.user_repository import UserRepository
from app.services.private_channel_service import PrivateChannelService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)
router = Router(name="user_join_request")


@router.chat_join_request()
async def on_chat_join_request(
    event: ChatJoinRequest, bot: Bot, session: AsyncSession, db_bot: BotModel
) -> None:
    """Fired by Telegram when a user taps a `creates_join_request=True`
    invite link. This is the ONLY place that actually grants access --
    everything earlier in the flow is just guidance/UX. Re-validating
    here (instead of trusting the earlier in-bot check) closes the race
    where a user unsubscribes between getting the link and using it.
    """
    pc_repo = PrivateChannelRepository(session)
    private_channel = await pc_repo.get_by_channel_chat_id(event.chat.id)

    analytics = AnalyticsRepository(session)
    users = UserRepository(session)
    user = await users.get_or_create(
        bot_id=db_bot.id,
        tg_id=event.from_user.id,
        username=event.from_user.username,
        full_name=event.from_user.full_name,
    )

    if private_channel is None:
        logger.warning("Join request for unmapped chat_id=%s on bot_id=%s", event.chat.id, db_bot.id)
        await bot.decline_chat_join_request(chat_id=event.chat.id, user_id=event.from_user.id)
        return

    await analytics.log(
        bot_id=db_bot.id,
        user_id=user.id,
        event_type=AnalyticsEventType.JOIN_REQUEST_RECEIVED,
        meta={"private_channel_id": private_channel.id},
    )

    subscription_service = SubscriptionService(bot, session, get_redis())
    pc_service = PrivateChannelService(session, subscription_service)
    await pc_service.handle_join_request(bot, user, private_channel)
