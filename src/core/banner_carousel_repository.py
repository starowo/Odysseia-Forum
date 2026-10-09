from datetime import datetime, timedelta
from typing import List, Optional, cast

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, desc, select

from models import BannerCarousel
from shared.time_utils import utc_now


class BannerCarouselRepository:
    """banner_carousel 表的数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active_for_status(self, now: datetime) -> List[BannerCarousel]:
        """批量获取所有未过期轮播，管理状态不截断超额记录。"""
        # 使用调用方提供的时间，统一查询和展示的时间口径。
        end_time_col = cast(ColumnElement, BannerCarousel.end_time)
        result = await self.session.execute(
            select(BannerCarousel)
            .where(end_time_col > now)
            .order_by(BannerCarousel.position, BannerCarousel.id)
        )
        return list(result.scalars().all())

    async def get_active(
        self, channel_ids: Optional[List[int]] = None, all_channels: bool = False
    ) -> List[BannerCarousel]:
        """批量获取指定频道及全局的有效轮播项。"""
        now = utc_now().replace(microsecond=0)
        channel_id_col = cast(ColumnElement, BannerCarousel.channel_id)
        end_time_col = cast(ColumnElement, BannerCarousel.end_time)
        position_col = cast(ColumnElement, BannerCarousel.position)
        ordered_channel_ids = list(dict.fromkeys(channel_ids or []))

        if not ordered_channel_ids and not all_channels:
            result = await self.session.execute(
                select(BannerCarousel)
                .where(and_(channel_id_col.is_(None), end_time_col > now))
                .order_by(position_col, BannerCarousel.id)
                .limit(3)
            )
            return list(result.scalars().all())

        # 一次查询全部频道专属 Banner，再按请求频道顺序分组限量。
        channel_result = await self.session.execute(
            select(BannerCarousel)
            .where(
                and_(
                    channel_id_col.is_not(None) if all_channels else channel_id_col.in_(ordered_channel_ids),
                    end_time_col > now,
                )
            )
            .order_by(position_col, BannerCarousel.id)
        )
        grouped_banners: dict[int, list[BannerCarousel]] = {
            channel_id: [] for channel_id in ordered_channel_ids
        }
        for banner in channel_result.scalars().all():
            banner_channel_id = banner.channel_id
            if banner_channel_id is not None:
                grouped_banners.setdefault(banner_channel_id, []).append(banner)

        # 全部模式直接从轮播记录发现频道，不依赖搜索目录或配置。
        if all_channels:
            ordered_channel_ids = sorted(grouped_banners)

        channel_banners = [
            banner
            for channel_id in ordered_channel_ids
            for banner in grouped_banners[channel_id][:5]
        ]

        # 全局 Banner 只查询一次，并与频道候选按轮播记录 ID 合并排序。
        global_result = await self.session.execute(
            select(BannerCarousel)
            .where(and_(channel_id_col.is_(None), end_time_col > now))
            .order_by(position_col, BannerCarousel.id)
            .limit(3)
        )
        global_banners = list(global_result.scalars().all())

        return sorted(
            [*global_banners, *channel_banners],
            key=lambda banner: cast(int, banner.id),
        )

    async def get_count(self, channel_id: Optional[int]) -> int:
        """统计指定频道的当前有效轮播数。"""
        now = utc_now().replace(microsecond=0)
        channel_id_col = cast(ColumnElement, BannerCarousel.channel_id)
        end_time_col = cast(ColumnElement, BannerCarousel.end_time)

        result = await self.session.execute(
            select(BannerCarousel).where(
                and_(channel_id_col == channel_id, end_time_col > now)
            )
        )
        return len(result.scalars().all())

    async def get_expired(self) -> List[BannerCarousel]:
        """获取所有已过期的轮播项。"""
        now = utc_now().replace(microsecond=0)
        end_time_col = cast(ColumnElement, BannerCarousel.end_time)

        result = await self.session.execute(
            select(BannerCarousel).where(end_time_col <= now)
        )
        return list(result.scalars().all())

    async def get_by_thread(self, thread_id: int) -> List[BannerCarousel]:
        """按帖子 ID 查询轮播项。"""
        result = await self.session.execute(
            select(BannerCarousel).where(BannerCarousel.thread_id == thread_id)
        )
        return list(result.scalars().all())

    async def add(
        self,
        thread_id: int,
        channel_id: Optional[int],
        cover_image_url: str | None,
        title: str,
        duration_days: int,
        target_type: int = 1,
    ) -> None:
        """插入一条轮播记录（含 position 计算）。"""
        start_time = utc_now().replace(microsecond=0)
        end_time = start_time + timedelta(days=duration_days)
        channel_id_col = cast(ColumnElement, BannerCarousel.channel_id)
        end_time_col = cast(ColumnElement, BannerCarousel.end_time)
        position_col = cast(ColumnElement, BannerCarousel.position)

        result = await self.session.execute(
            select(position_col)
            .where(and_(channel_id_col == channel_id, end_time_col > start_time))
            .order_by(desc(position_col))
            .limit(1)
        )
        max_position = result.scalar_one_or_none()
        new_position = (max_position + 1) if max_position is not None else 0

        item = BannerCarousel(
            thread_id=thread_id,
            channel_id=channel_id,
            cover_image_url=cover_image_url,
            title=title,
            target_type=target_type,
            start_time=start_time,
            end_time=end_time,
            position=new_position,
        )
        self.session.add(item)

    async def delete(self, item: BannerCarousel) -> None:
        """从会话中移除一条轮播记录。"""
        await self.session.delete(item)
