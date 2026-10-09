from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from models import BannerApplication
from shared.enum import ApplicationStatus


class BannerApplicationRepository:
    """banner_application 表的数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        thread_id: int,
        channel_id: int,
        applicant_id: int,
        cover_image_url: str | None,
        target_scope: str,
        target_type: int = 1,
    ) -> BannerApplication:
        """插入一条 PENDING 状态的申请记录。"""
        application = BannerApplication(
            thread_id=thread_id,
            channel_id=channel_id,
            applicant_id=applicant_id,
            cover_image_url=cover_image_url,
            target_scope=target_scope,
            target_type=target_type,
            status=ApplicationStatus.PENDING.value,
            applied_at=datetime.now().replace(microsecond=0),
        )
        self.session.add(application)
        await self.session.flush()
        return application

    async def get_by_id(self, application_id: int) -> Optional[BannerApplication]:
        """按主键查询。"""
        result = await self.session.execute(
            select(BannerApplication).where(BannerApplication.id == application_id)
        )
        return result.scalar_one_or_none()

    async def get_by_review_message(
        self, review_message_id: int
    ) -> Optional[BannerApplication]:
        """通过审核消息 ID 反查。"""
        result = await self.session.execute(
            select(BannerApplication).where(
                BannerApplication.review_message_id == review_message_id
            )
        )
        return result.scalar_one_or_none()

    async def get_history_by_thread_id(self, thread_id: int) -> List[BannerApplication]:
        """查询同一 thread_id 的非 pending 申请，按 applied_at 倒序。

        仅返回有 review_message_id 的记录，确保能生成审核消息跳转链接。
        """
        result = await self.session.execute(
            select(BannerApplication)
            .where(
                BannerApplication.thread_id == thread_id,
                BannerApplication.status != ApplicationStatus.PENDING.value,
                BannerApplication.review_message_id.is_not(None),
            )
            .order_by(desc(BannerApplication.applied_at))
        )
        return list(result.scalars().all())

    async def update_review_message_info(
        self,
        application_id: int,
        review_message_id: int,
        review_thread_id: int,
    ) -> bool:
        """回填审核消息 ID 和所在线程 ID。"""
        result = await self.session.execute(
            select(BannerApplication).where(BannerApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        if application:
            application.review_message_id = review_message_id
            application.review_thread_id = review_thread_id
            return True
        return False
