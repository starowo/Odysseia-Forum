import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models.booklist_publish import BooklistPublish
from shared.time_utils import utc_now

logger = logging.getLogger(__name__)


class BooklistPublishRepository:
    """书单发布记录仓库层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        booklist_id: int,
        guild_id: int,
        thread_id: int,
        discord_user_id: int,
    ) -> BooklistPublish:
        """按书单原子创建或更新唯一发布记录。"""
        # 事务锁负责串行化“查询后更新/替换”，唯一约束负责兜底数据不变量。
        await self.session.execute(select(func.pg_advisory_xact_lock(booklist_id)))

        record = await self.get_by_booklist(booklist_id)
        if record is None:
            record = BooklistPublish(
                booklist_id=booklist_id,
                guild_id=guild_id,
                thread_id=thread_id,
                discord_user_id=discord_user_id,
            )
            self.session.add(record)
        else:
            target_changed = (
                record.guild_id != guild_id or record.thread_id != thread_id
            )
            if target_changed:
                old_record_id = record.id
                await self.session.delete(record)
                await self.session.flush()
                record = BooklistPublish(
                    booklist_id=booklist_id,
                    guild_id=guild_id,
                    thread_id=thread_id,
                    discord_user_id=discord_user_id,
                )
                self.session.add(record)
                logger.info(
                    "书单 %d 发布目标已变化，替换发布记录: old_id=%s",
                    booklist_id,
                    old_record_id,
                )
            else:
                record.discord_user_id = discord_user_id
                now = utc_now()
                # updated_at 同时作为同目标连续发布的本地请求版本。
                if now <= record.updated_at:
                    now = record.updated_at + timedelta(microseconds=1)
                record.updated_at = now

        await self.session.commit()
        await self.session.refresh(record)
        logger.info(
            "书单 %d 发布记录已写入: record_id=%s, thread_id=%d",
            booklist_id,
            record.id,
            thread_id,
        )
        return record

    async def get_by_booklist(self, booklist_id: int) -> Optional[BooklistPublish]:
        """获取书单的唯一发布记录。"""
        stmt = select(BooklistPublish).where(
            BooklistPublish.booklist_id == booklist_id  # type: ignore
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_current_request(
        self, booklist_id: int, record_id: int, request_updated_at: datetime
    ) -> bool:
        """检查给定记录与更新时间是否仍代表书单的最新发布请求。"""
        stmt = (
            select(BooklistPublish.id)
            .where(
                BooklistPublish.booklist_id == booklist_id,  # type: ignore
                BooklistPublish.id == record_id,  # type: ignore
                BooklistPublish.updated_at == request_updated_at,  # type: ignore
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def lock_current_request(
        self, booklist_id: int, record_id: int, request_updated_at: datetime
    ) -> bool:
        """锁定并确认当前发布请求，供同事务内更新书单状态。"""
        stmt = (
            select(BooklistPublish.id)
            .where(
                BooklistPublish.booklist_id == booklist_id,  # type: ignore
                BooklistPublish.id == record_id,  # type: ignore
                BooklistPublish.updated_at == request_updated_at,  # type: ignore
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update_message_if_current(
        self,
        booklist_id: int,
        record_id: int,
        request_updated_at: datetime,
        message_id: Optional[int],
        message_url: Optional[str],
    ) -> bool:
        """仅当请求仍为最新时更新 Discord 消息信息，不提交事务。"""
        stmt = (
            update(BooklistPublish)
            .where(
                BooklistPublish.booklist_id == booklist_id,  # type: ignore
                BooklistPublish.id == record_id,  # type: ignore
                BooklistPublish.updated_at == request_updated_at,  # type: ignore
            )
            .values(message_id=message_id, message_url=message_url)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete_by_booklist(self, booklist_id: int) -> int:
        """删除书单的所有发布记录，返回删除数量"""
        stmt = delete(BooklistPublish).where(
            BooklistPublish.booklist_id == booklist_id  # type: ignore
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        deleted = result.rowcount
        if deleted:
            logger.info("书单 %d 的 %d 条发布记录已删除", booklist_id, deleted)
        return deleted

    async def is_published(self, booklist_id: int) -> bool:
        """检查书单是否有任何发布记录"""
        stmt = (
            select(BooklistPublish.id)
            .where(
                BooklistPublish.booklist_id == booklist_id  # type: ignore
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
