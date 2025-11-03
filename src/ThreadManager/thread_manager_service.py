import logging
from typing import List, Sequence, cast
from datetime import datetime
from shared.models.tag_vote import TagVote
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, ColumnElement, case
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from shared.models.thread import Thread
from shared.models.tag import Tag
from shared.models.thread_tag_link import ThreadTagLink
from .update_data_dto import UpdateData

logger = logging.getLogger(__name__)


class ThreadManagerService:
    """封装与标签系统相关的数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_tags(self, tags_data: dict[int, str]) -> List[Tag]:
        """
        根据标签ID和名称的字典，获取或创建标签对象。
        """
        if not tags_data:
            return []

        tag_ids = list(tags_data.keys())
        values_to_insert = [{"id": id, "name": name} for id, name in tags_data.items()]

        # 1. 使用 INSERT ... ON CONFLICT DO UPDATE 一次性完成创建和更新
        insert_stmt = sqlite_insert(Tag).values(values_to_insert)

        # 构建 ON CONFLICT ... DO UPDATE 子句
        # 当 'id' 冲突时，更新 'name' 字段
        # 'excluded' 是一个特殊的对象，代表了在 INSERT 语句中试图插入的值
        update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["id"], set_={"name": insert_stmt.excluded.name}
        )

        await self.session.execute(update_stmt)

        # 2. 查询所有相关的标签对象
        final_statement = select(Tag).where(cast(ColumnElement, Tag.id).in_(tag_ids))
        result = await self.session.execute(final_statement)
        return list(result.scalars().all())

    async def add_or_update_thread_with_tags(
        self, thread_data: dict, tags_data: dict[int, str]
    ):
        """
        添加或更新一个帖子及其标签。
        """
        # 查找现有帖子
        statement = (
            select(Thread)
            .where(Thread.thread_id == thread_data["thread_id"])
            .options(selectinload(Thread.tags))  # type: ignore
        )
        result = await self.session.execute(statement)
        db_thread = result.scalars().first()

        # 获取或创建所有相关标签
        tags = await self.get_or_create_tags(tags_data)

        if db_thread:
            # 更新帖子
            for key, value in thread_data.items():
                setattr(db_thread, key, value)

            # 非破坏性地更新标签，以保留 ThreadTagLink 中的投票数据
            current_tag_ids = {tag.id for tag in db_thread.tags}
            new_tag_ids = set(tags_data.keys())

            tags_to_add_ids = new_tag_ids - current_tag_ids
            tags_to_remove_ids = current_tag_ids - new_tag_ids

            # 移除不再需要的标签关联
            if tags_to_remove_ids:
                db_thread.tags = [
                    t for t in db_thread.tags if t.id not in tags_to_remove_ids
                ]

            # 添加新的标签关联
            if tags_to_add_ids:
                tags_to_add = [t for t in tags if t.id in tags_to_add_ids]
                db_thread.tags.extend(tags_to_add)

            self.session.add(db_thread)
        else:
            # 创建新帖子
            new_thread = Thread(**thread_data)
            new_thread.tags = tags
            self.session.add(new_thread)
        await self.session.commit()

    async def delete_thread_index(self, thread_id: int):
        """删除帖子的所有相关索引数据"""
        statement = select(Thread).where(Thread.thread_id == thread_id)  # type: ignore
        result = await self.session.execute(statement)
        db_thread = result.scalars().first()
        if db_thread:
            await self.session.delete(db_thread)
            await self.session.commit()

    async def update_thread_activity(
        self, thread_id: int, last_active_at: datetime, reply_count: int
    ):
        """仅更新帖子的活跃时间和回复数"""
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
        """仅更新帖子的最后活跃时间"""
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
        """仅更新帖子的反应数。如果更新成功（至少影响了一行），则返回 True，否则返回 False。"""
        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore
            .values(reaction_count=reaction_count)
        )
        # 执行语句并获取结果对象
        result = await self.session.execute(stmt)
        await self.session.commit()
        # 返回 rowcount 是否大于 0
        return result.rowcount > 0

    async def get_tags_for_channels(self, channel_ids: List[int]) -> Sequence[Tag]:
        """获取指定频道列表内的所有唯一标签"""
        statement = (
            select(Tag)
            .join(Thread, Tag.threads)  # type: ignore
            .where(cast(ColumnElement, Thread.channel_id).in_(channel_ids))
            .distinct()
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_all_tags(self) -> Sequence[Tag]:
        """获取数据库中所有的标签。"""
        statement = select(Tag)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def update_tag_name(self, tag_id: int, new_name: str):
        """更新指定ID的标签的名称。"""
        statement = select(Tag).where(Tag.id == tag_id)  # type: ignore
        result = await self.session.execute(statement)
        tag = result.scalars().first()
        if tag:
            tag.name = new_name
            self.session.add(tag)
            await self.session.commit()

    async def record_tag_vote(
        self,
        user_id: int,
        thread_id: int,
        tag_id: int,
        vote_value: int,
        tag_map: dict[int, str],
    ) -> dict:
        """
        记录一次标签投票，并更新 ThreadTagLink 表中的 upvotes 和 downvotes。
        """
        # 查找帖子对象以获取其内部ID
        thread_statement = select(Thread).where(Thread.thread_id == thread_id)  # type: ignore
        thread_result = await self.session.execute(thread_statement)
        db_thread = thread_result.scalars().first()
        if not db_thread or not db_thread.id:
            logger.warning(f"record_tag_vote: 未找到 thread_id={thread_id} 的帖子。")
            return {}

        # 查找对应的 ThreadTagLink 记录
        link_stmt = select(ThreadTagLink).where(
            ThreadTagLink.thread_id == db_thread.id,
            ThreadTagLink.tag_id == tag_id,  # type: ignore
        )
        link_result = await self.session.execute(link_stmt)
        link_record = link_result.scalars().first()
        if not link_record:
            logger.warning(f"record_tag_vote: 帖子 {thread_id} 并未应用标签 {tag_id}。")
            return await self.get_tag_vote_stats(thread_id, tag_map)

        # 查找现有投票
        vote_stmt = select(TagVote).where(
            TagVote.user_id == user_id,  # type: ignore
            TagVote.thread_id == db_thread.id,  # type: ignore
            TagVote.tag_id == tag_id,  # type: ignore
        )
        vote_result = await self.session.execute(vote_stmt)
        existing_vote = vote_result.scalars().first()

        if existing_vote:
            previous_vote = existing_vote.vote
            if previous_vote == vote_value:  # 取消投票
                if previous_vote == 1:
                    link_record.upvotes -= 1
                else:
                    link_record.downvotes -= 1
                await self.session.delete(existing_vote)
            else:  # 更改投票
                if previous_vote == 1:
                    link_record.upvotes -= 1
                else:
                    link_record.downvotes -= 1

                if vote_value == 1:
                    link_record.upvotes += 1
                else:
                    link_record.downvotes += 1
                existing_vote.vote = vote_value
                self.session.add(existing_vote)
        else:  # 新投票
            if vote_value == 1:
                link_record.upvotes += 1
            else:
                link_record.downvotes += 1
            new_vote = TagVote(
                user_id=user_id, thread_id=db_thread.id, tag_id=tag_id, vote=vote_value
            )
            self.session.add(new_vote)

        self.session.add(link_record)
        await self.session.commit()

        # 返回该帖子的最新完整统计数据
        return await self.get_tag_vote_stats(thread_id, tag_map)

    async def get_tag_vote_stats(self, thread_id: int, tag_map: dict[int, str]) -> dict:
        """
        获取一个帖子的标签投票统计。
        从与该帖子关联的 ThreadTagLink 记录中聚合数据。
        """
        thread_stmt = select(Thread).where(Thread.thread_id == thread_id)  # type: ignore
        result = await self.session.execute(thread_stmt)
        db_thread = result.scalars().first()

        if not db_thread:
            return {}

        # 查询所有与该帖子相关的 ThreadTagLink 记录
        link_stmt = select(ThreadTagLink).where(ThreadTagLink.thread_id == db_thread.id)  # type: ignore
        link_results = await self.session.execute(link_stmt)
        link_records = link_results.scalars().all()

        stats = {}
        for record in link_records:
            tag_name = tag_map.get(record.tag_id)
            if tag_name:
                stats[tag_name] = {
                    "upvotes": record.upvotes,
                    "downvotes": record.downvotes,
                    "score": record.upvotes - record.downvotes,
                }

        return stats

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
        从给定的ID列表中，查询并返回那些在数据库中真实存在的ID。
        """
        if not thread_ids:
            return []

        stmt = select(Thread.thread_id).where(
            cast(ColumnElement, Thread.thread_id).in_(thread_ids)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_not_found_count(self, thread_id: int) -> bool:
        """当找不到帖子时，将其 not_found_count 计数加一。"""
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
                latest_update_at=datetime.now(timezone.utc),
                latest_update_link=latest_update_link,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
