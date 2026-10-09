from datetime import datetime
from typing import List, Optional, cast

from sqlalchemy import ColumnElement, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from models import BannerWaitlist


class BannerWaitlistRepository:
    """banner_waitlist 表的数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_counts_by_scope(self) -> dict[int | None, int]:
        """一次查询所有展示范围的已审核待展示数量。"""
        # 按展示范围聚合，避免为每个频道单独查询。
        channel_id_col = cast(ColumnElement, BannerWaitlist.channel_id)
        result = await self.session.execute(
            select(channel_id_col, func.count()).group_by(channel_id_col)
        )
        return {channel_id: count for channel_id, count in result.all()}

    async def get_by_thread(self, thread_id: int) -> List[BannerWaitlist]:
        """按帖子 ID 查询等待项。"""
        result = await self.session.execute(
            select(BannerWaitlist).where(BannerWaitlist.thread_id == thread_id)
        )
        return list(result.scalars().all())

    async def has_item(self, channel_id: Optional[int]) -> bool:
        """检查等待队列中是否存在指定频道的项。"""
        channel_id_col = cast(ColumnElement, BannerWaitlist.channel_id)

        result = await self.session.execute(
            select(BannerWaitlist).where(channel_id_col == channel_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def add(
        self,
        thread_id: int,
        channel_id: Optional[int],
        cover_image_url: str | None,
        title: str,
        target_type: int = 1,
    ) -> None:
        """插入一条等待记录（含 position 计算）。"""
        now = datetime.now().replace(microsecond=0)
        channel_id_col = cast(ColumnElement, BannerWaitlist.channel_id)
        position_col = cast(ColumnElement, BannerWaitlist.position)

        result = await self.session.execute(
            select(position_col)
            .where(channel_id_col == channel_id)
            .order_by(desc(position_col))
            .limit(1)
        )
        max_position = result.scalar_one_or_none()
        new_position = (max_position + 1) if max_position is not None else 0

        item = BannerWaitlist(
            thread_id=thread_id,
            channel_id=channel_id,
            cover_image_url=cover_image_url,
            title=title,
            target_type=target_type,
            queued_at=now,
            position=new_position,
        )
        self.session.add(item)

    async def pop(self, channel_id: Optional[int]) -> Optional[BannerWaitlist]:
        """取出并删除排在最前面的等待项。"""
        channel_id_col = cast(ColumnElement, BannerWaitlist.channel_id)
        position_col = cast(ColumnElement, BannerWaitlist.position)

        result = await self.session.execute(
            select(BannerWaitlist)
            .where(channel_id_col == channel_id)
            .order_by(position_col)
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if item:
            await self.session.delete(item)
        return item

    async def delete(self, item: BannerWaitlist) -> None:
        """从会话中移除一条等待项。"""
        await self.session.delete(item)
