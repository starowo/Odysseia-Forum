import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col

from core.notification_fanout_service import NotificationFanoutService
from core.notification_repository import NotificationRepository
from core.thread_update_error import ThreadUpdateError
from core.thread_update_repository import ThreadUpdateRepository
from dto.thread_update_dto import ThreadUpdateDTO
from models import Thread, ThreadUpdate
from shared.time_utils import utc_now

logger = logging.getLogger(__name__)


class ThreadUpdateService:
    """原子维护作品更新历史、最新投影和动态通知。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def publish(
        self,
        thread_id: int,
        message_id: int,
        publisher_id: int,
        description: str,
        version: str | None,
        source_message_at: datetime,
    ) -> ThreadUpdateDTO:
        """正式发布一条作品更新。"""
        clean_description, clean_version = self._normalize_info(description, version)
        async with self.session_factory() as session:
            try:
                thread = await self._get_publishable_thread(
                    session, thread_id, publisher_id
                )
                update_repository = ThreadUpdateRepository(session)
                if await update_repository.get_by_message_id(message_id):
                    raise ThreadUpdateError("该消息已经发布过更新")

                published_at = utc_now()
                update_record = await update_repository.add(
                    ThreadUpdate(
                        thread_id=thread_id,
                        message_id=message_id,
                        publisher_id=publisher_id,
                        description=clean_description,
                        version=clean_version,
                        source_message_at=source_message_at,
                        published_at=published_at,
                    )
                )
                if update_record.id is None:
                    raise RuntimeError("新增作品更新后未取得主键")

                thread.latest_update_id = update_record.id
                thread.latest_update_at = published_at
                thread.latest_update_link = self.build_message_link(
                    thread.guild_id, thread_id, message_id
                )
                session.add(thread)

                # 在当前事务中直接从关注关系生成通知
                await NotificationFanoutService(session).fanout_thread_update(
                    thread_id=thread_id,
                    publisher_id=publisher_id,
                    event_source_id=update_record.id,
                    created_at=published_at,
                )
                update_dto = self._to_dto(update_record)
                await session.commit()
                return update_dto
            except ThreadUpdateError:
                await session.rollback()
                raise
            except IntegrityError as exc:
                await session.rollback()
                raise ThreadUpdateError("该消息已经发布过更新") from exc
            except Exception:
                await session.rollback()
                raise

    async def edit(
        self,
        update_id: int,
        publisher_id: int,
        description: str,
        version: str | None,
    ) -> ThreadUpdateDTO:
        """修改已发布更新的描述与版本。"""
        clean_description, clean_version = self._normalize_info(description, version)
        async with self.session_factory() as session:
            repository = ThreadUpdateRepository(session)
            update_record = await repository.get_by_id(update_id)
            if update_record is None:
                raise ThreadUpdateError("此次发布不存在或已被删除")
            if update_record.publisher_id != publisher_id:
                raise ThreadUpdateError("只有发布者可以修改此次发布")
            update_record.description = clean_description
            update_record.version = clean_version
            session.add(update_record)
            update_dto = self._to_dto(update_record)
            await session.commit()
            return update_dto

    async def delete(self, update_id: int, publisher_id: int) -> ThreadUpdateDTO:
        """撤销一次发布并在必要时回滚作品最新投影。"""
        async with self.session_factory() as session:
            try:
                repository = ThreadUpdateRepository(session)
                update_record = await repository.get_by_id(update_id)
                if update_record is None:
                    raise ThreadUpdateError("此次发布不存在或已被删除")
                if update_record.publisher_id != publisher_id:
                    raise ThreadUpdateError("只有发布者可以删除此次发布")
                deleted_dto = self._to_dto(update_record)

                notification_repository = NotificationRepository(session)
                await notification_repository.delete_for_event(
                    "thread_update", update_id
                )
                await repository.delete(update_record)

                thread_statement = select(Thread).where(
                    col(Thread.thread_id) == update_record.thread_id
                )
                thread = (await session.execute(thread_statement)).scalar_one_or_none()
                if thread is not None and thread.latest_update_id == update_id:
                    previous = await repository.get_latest_for_thread(
                        update_record.thread_id
                    )
                    if previous is None:
                        thread.latest_update_id = None
                        thread.latest_update_at = None
                        thread.latest_update_link = None
                    else:
                        thread.latest_update_id = previous.id
                        thread.latest_update_at = previous.published_at
                        if previous.message_id is None:
                            thread.latest_update_link = None
                        else:
                            thread.latest_update_link = self.build_message_link(
                                thread.guild_id,
                                thread.thread_id,
                                previous.message_id,
                            )
                    session.add(thread)
                await session.commit()
                return deleted_dto
            except ThreadUpdateError:
                await session.rollback()
                raise
            except Exception:
                await session.rollback()
                raise

    async def set_overview_message_id(
        self, update_id: int, overview_message_id: int
    ) -> None:
        """在 Discord 发送成功后记录自动发布概览消息。"""
        async with self.session_factory() as session:
            repository = ThreadUpdateRepository(session)
            update_record = await repository.get_by_id(update_id)
            if update_record is None:
                return
            update_record.overview_message_id = overview_message_id
            session.add(update_record)
            await session.commit()

    async def get_by_overview_message_id(
        self, overview_message_id: int
    ) -> ThreadUpdateDTO | None:
        """按概览消息 ID 获取更新数据。"""
        async with self.session_factory() as session:
            record = await ThreadUpdateRepository(session).get_by_overview_message_id(
                overview_message_id
            )
            return self._to_dto(record) if record else None

    @staticmethod
    def build_message_link(guild_id: int, thread_id: int, message_id: int) -> str:
        """构建 Discord 消息永久链接。"""
        return f"https://discord.com/channels/{guild_id}/{thread_id}/{message_id}"

    @staticmethod
    def _normalize_info(
        description: str, version: str | None
    ) -> tuple[str, str | None]:
        """清理并校验发布描述与版本号。"""
        clean_description = description.strip()
        clean_version = version.strip() if version else None
        if not 1 <= len(clean_description) <= 500:
            raise ThreadUpdateError("更新说明长度必须为 1-500 字")
        if clean_version is not None and not 1 <= len(clean_version) <= 50:
            raise ThreadUpdateError("版本长度必须为 1-50 字")
        return clean_description, clean_version

    @staticmethod
    async def _get_publishable_thread(
        session: AsyncSession, thread_id: int, publisher_id: int
    ) -> Thread:
        """获取可发布更新的索引作品并校验作者。"""
        statement = select(Thread).where(col(Thread.thread_id) == thread_id)
        thread = (await session.execute(statement)).scalar_one_or_none()
        if thread is None or not thread.show_flag or thread.not_found_count > 0:
            raise ThreadUpdateError("当前帖子未索引或已不可见")
        if thread.author_id != publisher_id:
            raise ThreadUpdateError("你不是索引记录中的作品作者")
        return thread

    @staticmethod
    def _to_dto(record: ThreadUpdate) -> ThreadUpdateDTO:
        """将数据库实体转换为跨层 DTO。"""
        if record.id is None:
            raise RuntimeError("作品更新缺少主键")
        return ThreadUpdateDTO(
            id=record.id,
            thread_id=record.thread_id,
            message_id=record.message_id,
            publisher_id=record.publisher_id,
            description=record.description,
            version=record.version,
            source_message_at=record.source_message_at,
            published_at=record.published_at,
            overview_message_id=record.overview_message_id,
        )
