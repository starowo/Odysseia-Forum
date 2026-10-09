from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from models import AuthorFollow, Notification, ThreadFollow
from shared.time_utils import utc_now


class NotificationFanoutService:
    """通过数据库内查询为关注者批量生成动态通知。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def fanout_thread_update(
        self,
        thread_id: int,
        publisher_id: int,
        event_source_id: int,
        created_at: datetime,
    ) -> int:
        """为作品更新生成全部活跃帖子关注者通知。"""
        # 仅在数据库中选择活跃关注者，并排除更新发布者
        recipient_query = select(ThreadFollow.user_id.label("user_id")).where(
            ThreadFollow.thread_id == thread_id,
            ThreadFollow.active_flag.is_(True),
            ThreadFollow.user_id != publisher_id,
        )
        return await self._fanout(
            recipient_query=recipient_query,
            event_type="thread_update",
            event_source_id=event_source_id,
            thread_id=thread_id,
            created_at=created_at,
        )

    async def fanout_author_new_thread(
        self,
        author_id: int,
        thread_id: int,
        event_source_id: int,
        created_at: datetime | None = None,
    ) -> int:
        """为作者新作品生成全部活跃作者关注者通知。"""
        # 仅在数据库中选择活跃关注者，并排除作者本人
        recipient_query = select(AuthorFollow.user_id.label("user_id")).where(
            AuthorFollow.author_id == author_id,
            AuthorFollow.active_flag.is_(True),
            AuthorFollow.user_id != author_id,
        )
        return await self._fanout(
            recipient_query=recipient_query,
            event_type="author_new_thread",
            event_source_id=event_source_id,
            thread_id=thread_id,
            created_at=created_at or utc_now(),
        )

    async def _fanout(
        self,
        recipient_query: Select[tuple[int]],
        event_type: str,
        event_source_id: int,
        thread_id: int,
        created_at: datetime,
    ) -> int:
        """将接收者查询直接转换为幂等通知插入语句。"""
        recipient_subquery = recipient_query.subquery()

        # 使用固定数量的绑定参数构造通知数据，避免关注者数量影响参数数量
        notification_rows = select(
            recipient_subquery.c.user_id,
            literal(event_type, type_=String(32)),
            literal(event_source_id, type_=BigInteger()),
            literal(thread_id, type_=BigInteger()),
            literal(created_at, type_=DateTime()),
        )
        statement = (
            insert(Notification)
            .from_select(
                [
                    "user_id",
                    "event_type",
                    "event_source_id",
                    "thread_id",
                    "created_at",
                ],
                notification_rows,
            )
            .on_conflict_do_nothing(constraint="uk_notification_user_event_source")
        )
        result = await self.session.execute(statement)
        return int(result.rowcount or 0)
