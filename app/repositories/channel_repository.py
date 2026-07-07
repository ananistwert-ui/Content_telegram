from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import Channel, ChannelRequirement, PrivateChannel
from app.models.enums import ChannelType
from app.repositories.base import BaseRepository


class ChannelRepository(BaseRepository[Channel]):
    model = Channel

    async def list_for_bot(self, bot_id: int, type_: ChannelType | None = None) -> list[Channel]:
        stmt = select(Channel).where(Channel.bot_id == bot_id, Channel.is_active.is_(True))
        if type_ is not None:
            stmt = stmt.where(Channel.type == type_)
        return list((await self.session.execute(stmt)).scalars().all())


class PrivateChannelRepository(BaseRepository[PrivateChannel]):
    model = PrivateChannel

    async def list_for_bot(self, bot_id: int) -> list[PrivateChannel]:
        stmt = (
            select(PrivateChannel)
            .where(PrivateChannel.bot_id == bot_id, PrivateChannel.is_active.is_(True))
            .options(
                selectinload(PrivateChannel.channel),
                selectinload(PrivateChannel.requirements).selectinload(ChannelRequirement.required_channel),
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_with_requirements(self, private_channel_id: int) -> PrivateChannel | None:
        stmt = (
            select(PrivateChannel)
            .where(PrivateChannel.id == private_channel_id)
            .options(
                selectinload(PrivateChannel.channel),
                selectinload(PrivateChannel.requirements).selectinload(ChannelRequirement.required_channel),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_invite_link(self, invite_link: str) -> PrivateChannel | None:
        stmt = (
            select(PrivateChannel)
            .where(PrivateChannel.invite_link == invite_link)
            .options(
                selectinload(PrivateChannel.channel),
                selectinload(PrivateChannel.requirements).selectinload(ChannelRequirement.required_channel),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_channel_chat_id(self, tg_chat_id: int) -> PrivateChannel | None:
        stmt = (
            select(PrivateChannel)
            .join(Channel, Channel.id == PrivateChannel.channel_id)
            .where(Channel.tg_chat_id == tg_chat_id)
            .options(
                selectinload(PrivateChannel.channel),
                selectinload(PrivateChannel.requirements).selectinload(ChannelRequirement.required_channel),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
