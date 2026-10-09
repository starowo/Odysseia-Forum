from core.tag_binding_repository import TagBindingRepository
import logging
from datetime import datetime
from collections.abc import AsyncIterator
from typing import List, Optional, Sequence, cast

from sqlalchemy import ColumnElement, case, delete, func, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from dto.meta import ChannelThreadCount
from dto.open_graph import (
    AuthorStatsQueryDTO,
    OpenGraphLatestWorkDTO,
    OpenGraphWorkCandidateDTO,
    ThreadShareQueryDTO,
)
from dto.search.fts_result_dto import FTSResultDTO
from dto.thread_sync_mutation_result import ThreadSyncMutationResult
from dto.update_data import UpdateData
from models import Author, Tag, Thread, ThreadFollow
from models.booklist_item import BooklistItem
from models.user_collection import UserCollection
from shared.enum import CollectionType
from shared.fts_utils import build_fts_conditions

logger = logging.getLogger(__name__)


class ThreadRepository:
    """封装与 Thread 表相关的数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_open_graph_thread(
        self, thread_id: int, excluded_channel_ids: set[int]
    ) -> ThreadShareQueryDTO | None:
        """查询一个可公开分享的帖子及其作者标量信息。"""
        # 外连接作者，作者记录缺失时仍允许帖子以“未命名”作者展示。
        statement = (
            select(
                Thread.thread_id,
                Thread.title,
                Thread.first_message_excerpt,
                Thread.thumbnail_urls,
                Thread.reaction_count,
                Thread.reply_count,
                Thread.collection_count,
                Thread.created_at,
                Thread.last_active_at,
                Author.display_name,
                Author.avatar_url,
            )
            .outerjoin(Author, Author.id == Thread.author_id)
            .where(
                Thread.thread_id == thread_id,
                Thread.show_flag.is_(True),  # type: ignore[attr-defined]
                Thread.not_found_count == 0,
            )
        )
        if excluded_channel_ids:
            statement = statement.where(
                Thread.channel_id.not_in(excluded_channel_ids)  # type: ignore[attr-defined]
            )
        row = (await self.session.execute(statement)).first()
        if row is None:
            return None
        return ThreadShareQueryDTO(
            thread_id=int(row.thread_id),
            title=row.title,
            description=row.first_message_excerpt,
            thumbnail_urls=list(row.thumbnail_urls or []),
            author_name=row.display_name,
            author_avatar_url=row.avatar_url,
            reaction_count=int(row.reaction_count or 0),
            reply_count=int(row.reply_count or 0),
            collection_count=int(row.collection_count or 0),
            created_at=row.created_at,
            updated_at=row.last_active_at or row.created_at,
        )

    async def get_open_graph_author_stats(
        self, author_id: int, excluded_channel_ids: set[int]
    ) -> AuthorStatsQueryDTO:
        """聚合作者全部可公开作品的数量、反应与回复统计。"""
        statement = select(
            func.count(Thread.id).label("thread_count"),
            func.coalesce(func.sum(Thread.reaction_count), 0).label("reaction_count"),
            func.coalesce(func.sum(Thread.reply_count), 0).label("reply_count"),
        ).where(
            Thread.author_id == author_id,
            Thread.show_flag.is_(True),  # type: ignore[attr-defined]
            Thread.not_found_count == 0,
        )
        if excluded_channel_ids:
            statement = statement.where(
                Thread.channel_id.not_in(excluded_channel_ids)  # type: ignore[attr-defined]
            )
        row = (await self.session.execute(statement)).one()
        return AuthorStatsQueryDTO(
            thread_count=int(row.thread_count or 0),
            reaction_count=int(row.reaction_count or 0),
            reply_count=int(row.reply_count or 0),
        )

    async def get_open_graph_latest_author_work(
        self, author_id: int, excluded_channel_ids: set[int]
    ) -> OpenGraphLatestWorkDTO | None:
        """按创建时间与帖子 ID 稳定选择作者最新公开作品。"""
        statement = (
            select(Thread.title, Thread.created_at)
            .where(
                Thread.author_id == author_id,
                Thread.show_flag.is_(True),  # type: ignore[attr-defined]
                Thread.not_found_count == 0,
            )
            .order_by(Thread.created_at.desc(), Thread.id.asc())
            .limit(1)
        )
        if excluded_channel_ids:
            statement = statement.where(
                Thread.channel_id.not_in(excluded_channel_ids)  # type: ignore[attr-defined]
            )
        row = (await self.session.execute(statement)).first()
        if row is None:
            return None
        return OpenGraphLatestWorkDTO(title=row.title, created_at=row.created_at)

    async def stream_open_graph_author_works(
        self, author_id: int, excluded_channel_ids: set[int]
    ) -> AsyncIterator[OpenGraphWorkCandidateDTO]:
        """按热度与稳定次序流式返回作者代表作品候选。"""
        statement = (
            select(
                Thread.thread_id,
                Thread.title,
                Thread.thumbnail_urls,
                Thread.reaction_count,
                Thread.created_at,
            )
            .where(
                Thread.author_id == author_id,
                Thread.show_flag.is_(True),  # type: ignore[attr-defined]
                Thread.not_found_count == 0,
            )
            .order_by(
                Thread.reaction_count.desc(),
                Thread.created_at.desc(),
                Thread.id.asc(),
            )
        )
        if excluded_channel_ids:
            statement = statement.where(
                Thread.channel_id.not_in(excluded_channel_ids)  # type: ignore[attr-defined]
            )
        result = await self.session.stream(statement)
        async for row in result:
            yield OpenGraphWorkCandidateDTO(
                thread_id=int(row.thread_id),
                title=row.title,
                thumbnail_urls=list(row.thumbnail_urls or []),
                reaction_count=int(row.reaction_count or 0),
                created_at=row.created_at,
            )

    async def are_open_graph_author_sources_valid(
        self,
        author_id: int,
        thread_ids: list[int],
        excluded_channel_ids: set[int],
    ) -> bool:
        """批量确认缓存来源帖子仍公开、非深渊且属于指定作者。"""
        unique_thread_ids = set(thread_ids)
        if not unique_thread_ids:
            return True
        statement = select(func.count(Thread.id)).where(
            Thread.thread_id.in_(unique_thread_ids),  # type: ignore[attr-defined]
            Thread.author_id == author_id,
            Thread.show_flag.is_(True),  # type: ignore[attr-defined]
            Thread.not_found_count == 0,
        )
        if excluded_channel_ids:
            statement = statement.where(
                Thread.channel_id.not_in(excluded_channel_ids)  # type: ignore[attr-defined]
            )
        count = (await self.session.execute(statement)).scalar_one()
        return int(count) == len(unique_thread_ids)

    async def add_or_update_thread_with_tags(
        self, thread_data: dict, tags: list[Tag]
    ) -> ThreadSyncMutationResult:
        """添加或更新帖子及标签并返回明确的变更结果。"""
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock_shared(73902141)")
        )
        # 查找现有帖子
        statement = (
            select(Thread)
            .where(Thread.thread_id == thread_data["thread_id"])
            .with_for_update()
            .options(selectinload(Thread.tags))  # type: ignore
        )
        result = await self.session.execute(statement)
        db_thread = result.scalars().first()

        if db_thread:
            created = False
            # 更新帖子
            for key, value in thread_data.items():
                setattr(db_thread, key, value)

            self.session.add(db_thread)
        else:
            db_thread = Thread(**thread_data)
            self.session.add(db_thread)
            created = True
        await self.session.flush()
        tags_changed = await TagBindingRepository(self.session).sync_native(
            db_thread.id, tags
        )
        if tags_changed:
            db_thread.native_tag_revision += 1
        await self.session.flush()
        return ThreadSyncMutationResult(
            created=created,
            tags_changed=tags_changed,
        )

    async def delete_thread_index(self, thread_id: int):
        """删除帖子记录"""
        statement = select(Thread).where(Thread.thread_id == thread_id)  # type: ignore
        result = await self.session.execute(statement)
        db_thread = result.scalars().first()
        if db_thread:
            await TagBindingRepository(self.session).delete_targets(
                "thread", [db_thread.id]
            )
            await self.session.delete(db_thread)
            await self.session.commit()

    async def delete_channel_index(self, channel_id: int):
        """删除指定 Discord 频道下的所有帖子索引及相关关联数据。"""
        # 查找该频道下所有 Thread 的内部 ID 和 Discord ID
        statement = select(Thread.id, Thread.thread_id).where(
            Thread.channel_id == channel_id
        )
        result = await self.session.execute(statement)
        rows = result.all()

        if not rows:
            logger.info(f"频道 {channel_id} 没有需要删除的索引帖子。")
            return

        thread_ids = [row[0] for row in rows]  # 内部主键 ID
        discord_ids = [row[1] for row in rows]  # Discord 帖子 ID

        try:
            await TagBindingRepository(self.session).delete_targets(
                "thread", thread_ids
            )

            # 删除 ThreadFollow 记录（依赖 Discord thread_id）
            delete_follows = delete(ThreadFollow).where(
                cast(ColumnElement, ThreadFollow.thread_id).in_(discord_ids)
            )
            await self.session.execute(delete_follows)

            # 删除 BooklistItem 记录（依赖 Discord thread_id）
            delete_items = delete(BooklistItem).where(
                cast(ColumnElement, BooklistItem.thread_id).in_(discord_ids)
            )
            await self.session.execute(delete_items)

            # 删除 UserCollection 记录（target_type=THREAD，依赖 Discord thread_id）
            delete_collections = delete(UserCollection).where(
                UserCollection.target_type == CollectionType.THREAD.value,
                cast(ColumnElement, UserCollection.target_id).in_(discord_ids),
            )
            await self.session.execute(delete_collections)

            # 删除 Thread 记录自身
            delete_threads = delete(Thread).where(
                cast(ColumnElement, Thread.id).in_(thread_ids)
            )
            await self.session.execute(delete_threads)

            await self.session.commit()
            logger.info(
                f"已删除频道 {channel_id} 的所有索引，"
                f"共 {len(thread_ids)} 个帖子及相关关联记录。"
            )
        except Exception:
            await self.session.rollback()
            logger.exception(f"删除频道 {channel_id} 的索引时发生数据库错误")
            raise

    async def update_thread_activity(
        self, thread_id: int, last_active_at: datetime, reply_count: int
    ):
        """更新帖子的活跃时间和回复数"""
        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore
            .values(
                last_active_at=last_active_at,
                reply_count=reply_count,
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_thread_last_active_at(
        self, thread_id: int, last_active_at: datetime
    ):
        """更新帖子的最后活跃时间"""
        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore
            .values(last_active_at=last_active_at)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_thread_reaction_count(
        self, thread_id: int, reaction_count: int
    ) -> bool:
        """更新帖子的反应数。如果更新成功（至少影响了一行），则返回 True，否则返回 False。"""
        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore
            .values(reaction_count=reaction_count)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def batch_update_thread_activity(self, updates: dict[int, UpdateData]) -> int:
        """
        批量更新多个帖子的活跃时间和回复数。

        Args:
            updates(dict[int, UpdateData]): {thread_id: {"increment": count, "last_active_at": datetime | None}}

        Returns:
            (int) 成功更新的行数。
        """
        if not updates:
            return 0

        thread_ids_to_update = list(updates.keys())

        # 构建 reply_count 的 CASE 表达式
        reply_count_case = case(
            {
                thread_id: Thread.reply_count + data["increment"]
                for thread_id, data in updates.items()
            },
            value=Thread.thread_id,
            else_=Thread.reply_count,  # 保持原值，如果ID不在case中
        )

        values_to_update = {"reply_count": reply_count_case}

        # 仅在存在有效 last_active_at 值时才构建和添加 case 表达式
        last_active_at_updates = {
            thread_id: data["last_active_at"]
            for thread_id, data in updates.items()
            if data["last_active_at"] is not None
        }

        if last_active_at_updates:
            last_active_at_case = case(
                last_active_at_updates,
                value=Thread.thread_id,
                else_=Thread.last_active_at,
            )
            values_to_update["last_active_at"] = last_active_at_case

        stmt = (
            update(Thread)
            .where(cast(ColumnElement, Thread.thread_id).in_(thread_ids_to_update))
            .values(**values_to_update)
            .execution_options(synchronize_session=False)
        )

        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_existing_thread_ids(self, thread_ids: List[int]) -> List[int]:
        """
        从给定的ID列表中，查询并返回那些在数据库中真实存在的记录ID
        """
        if not thread_ids:
            return []

        stmt = select(Thread.thread_id).where(
            cast(ColumnElement, Thread.thread_id).in_(thread_ids)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_not_found_count(self, thread_id: int) -> bool:
        """当找不到帖子时，将其 not_found_count 计数加一"""
        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore
            .values(not_found_count=Thread.not_found_count + 1)
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_thread_update_info(
        self, thread_id: int, latest_update_link: str
    ) -> bool:
        """
        更新帖子的最新更新时间和链接

        Args:
            thread_id: 帖子Discord ID
            latest_update_link: 最新版消息链接

        Returns:
            是否更新成功
        """
        from datetime import datetime, timezone

        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore
            .values(
                latest_update_at=datetime.now(timezone.utc).replace(tzinfo=None),
                latest_update_link=latest_update_link,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_collection_counts(self, thread_ids: List[int], delta: int) -> None:
        """批量更新帖子的被收藏次数"""
        if not thread_ids:
            return

        try:
            statement = (
                update(Thread)
                .where(Thread.thread_id.in_(thread_ids))  # type: ignore
                .values(collection_count=Thread.collection_count + delta)
                .execution_options(synchronize_session=False)
            )
            await self.session.execute(statement)
            await self.session.commit()
        except Exception as e:
            logger.error(f"批量更新帖子收藏数失败: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_thread_guild_id(self, thread_id: int) -> Optional[int]:
        """获取帖子的所属服务器 ID"""
        stmt = select(Thread.guild_id).where(Thread.thread_id == thread_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_thread_channel_id(self, thread_id: int) -> Optional[int]:
        """获取帖子所属的频道 ID（parent_id），用于 InactiveFollowBuffer 渠道校验。"""
        stmt = select(Thread.channel_id).where(Thread.thread_id == thread_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_thread_with_tags(self, thread_id: int) -> Optional[Thread]:
        """获取帖子及其标签（预加载）。"""
        stmt = (
            select(Thread)
            .where(Thread.thread_id == thread_id)
            .options(selectinload(Thread.tags))  # type: ignore[arg-type]
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_threads_by_ids_with_tags(self, thread_ids: list[int]) -> list[Thread]:
        """批量获取帖子及其标签（预加载），用于 Banner 等场景。"""
        if not thread_ids:
            return []
        stmt = (
            select(Thread)
            .where(Thread.thread_id.in_(thread_ids))  # type: ignore[arg-type]
            .options(
                selectinload(Thread.tags),  # type: ignore[arg-type]
                joinedload(Thread.author),  # type: ignore[arg-type]
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_indexed_channel_ids(self) -> Sequence[int]:
        """从数据库获取所有已索引的频道ID"""
        statement = select(Thread.channel_id).distinct()
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_thread_count_by_channels(
        self, channel_ids: List[int]
    ) -> List[ChannelThreadCount]:
        """批量获取指定频道列表中的有效帖子总数"""
        if not channel_ids:
            return []

        # 使用 cast 将 SQLModel 字段转换为 ColumnElement，以便在聚合查询中使用
        channel_id_column = cast(ColumnElement, Thread.channel_id)
        id_column = cast(ColumnElement, Thread.id)
        not_found_count_column = cast(ColumnElement, Thread.not_found_count)

        # 构建聚合查询：统计每个频道中 not_found_count 为 0 的有效帖子数
        statement = (
            select(channel_id_column, func.count(id_column))
            .where(channel_id_column.in_(channel_ids))
            .where(not_found_count_column == 0)
            .group_by(channel_id_column)
        )
        result = await self.session.execute(statement)
        rows = result.all()

        # 将查询结果转换为 DTO 列表
        return [
            ChannelThreadCount(channel_id=int(row[0]), thread_count=int(row[1]))
            for row in rows
        ]

    async def get_total_thread_count_for_scope(
        self, guild_id: Optional[int], channel_ids: Optional[List[int]]
    ) -> int:
        """获取指定范围内的有效帖子去重总数"""
        thread_id_column = cast(ColumnElement, Thread.id)
        not_found_count_column = cast(ColumnElement, Thread.not_found_count)
        guild_id_column = cast(ColumnElement, Thread.guild_id)
        channel_id_column = cast(ColumnElement, Thread.channel_id)

        statement = select(func.count(thread_id_column.distinct())).where(
            not_found_count_column == 0
        )

        if guild_id is not None:
            statement = statement.where(guild_id_column == guild_id)
        if channel_ids:
            statement = statement.where(channel_id_column.in_(channel_ids))

        result = await self.session.execute(statement)
        return result.scalar_one_or_none() or 0

    async def get_random_threads(
        self,
        limit: int,
        channel_ids: Optional[List[int]] = None,
        exclude_channel_ids: Optional[List[int]] = None,
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        tag_logic: str = "and",
    ) -> List[Thread]:
        """随机获取满足条件的帖子"""
        # 构建基础查询条件排除软删除帖子
        stmt = select(Thread).where(Thread.not_found_count == 0)

        # 只搜索 show_flag == True 的帖子，避免显示被隐藏的帖子
        stmt = stmt.where(Thread.show_flag)

        # 频道筛选
        if channel_ids:
            stmt = stmt.where(cast(ColumnElement, Thread.channel_id).in_(channel_ids))

        # 必须排除的频道筛选
        if exclude_channel_ids:
            stmt = stmt.where(
                ~cast(ColumnElement, Thread.channel_id).in_(exclude_channel_ids)
            )

        # 包含的标签筛选
        if include_tags:
            if tag_logic == "or":
                stmt = stmt.where(Thread.tags.any(Tag.name.in_(include_tags)))  # type: ignore
            else:
                for tag_name in include_tags:
                    stmt = stmt.where(Thread.tags.any(Tag.name == tag_name))  # type: ignore

        # 必须排除的标签
        if exclude_tags:
            stmt = stmt.where(~Thread.tags.any(Tag.name.in_(exclude_tags)))  # type: ignore

        # 使用数据库随机函数排序并限制返回数量
        stmt = stmt.order_by(func.random()).limit(limit)

        # 预加载标签和作者关联数据避免懒加载报错
        stmt = stmt.options(
            selectinload(Thread.tags),  # type: ignore
            joinedload(Thread.author),  # type: ignore
        )

        # 执行查询
        result = await self.session.execute(stmt)

        # 返回结果列表
        return list(result.scalars().all())

    async def update_thread_visibility(self, thread_id: int, show_flag: bool) -> bool:
        """更新帖子的搜索可见性状态"""
        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore
            .values(show_flag=show_flag)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_thread_thumbnail_urls(
        self, thread_id: int, thumbnail_urls: List[str]
    ) -> bool:
        """更新帖子的缩略图 URL 列表"""
        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore
            .values(thumbnail_urls=thumbnail_urls)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount)

    async def get_thread_visibility(self, thread_id: int) -> Optional[bool]:
        """获取帖子的可见性状态"""
        stmt = select(Thread.show_flag).where(Thread.thread_id == thread_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_thread_searchable(
        self,
        thread_id: int,
        exclude_channel_ids: list[int] | None = None,
    ) -> bool:
        """轻量校验帖子是否存在、可见且位于用户可访问的频道。"""
        filters = [
            Thread.thread_id == thread_id,
            Thread.not_found_count == 0,
            Thread.show_flag,
        ]
        if exclude_channel_ids:
            filters.append(
                Thread.channel_id.notin_(exclude_channel_ids)  # type: ignore[arg-type]
            )
        statement = select(Thread.thread_id).where(*filters).limit(1)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def get_fts_matched_thread_ids(
        self,
        keywords: str | None,
        exclude_keywords: str | None,
        exemption_markers: list[str] | None = None,
        redis_client=None,
    ) -> "FTSResultDTO":
        """
        处理 FTS 关键词搜索，返回可直接嵌入 WHERE 的 filter 条件。

        委托给共享模块 ``shared.fts_utils.build_fts_conditions``。
        """
        return await build_fts_conditions(
            Thread.search_vector,
            keywords,
            exclude_keywords,
            exemption_markers,
            redis_client,
        )
