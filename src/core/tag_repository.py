from core.discord_tag_source_repository import DiscordTagSourceRepository
import logging
from typing import Iterable, List, Sequence, cast

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models import Tag, Thread

logger = logging.getLogger(__name__)


class TagRepository:
    """封装与 Tag 表相关的数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_tags(
        self,
        tags_data: dict[int, str],
        update_names: bool = True,
        channel_id: int | None = None,
    ) -> List[Tag]:
        """解析原生来源返回标准概念；名称更新仅由完整频道快照负责。"""
        sources = await DiscordTagSourceRepository(self.session).ensure(
            tags_data, channel_id
        )
        if not sources:
            return []
        result = await self.session.execute(
            select(Tag).where(Tag.id.in_({s.tag_id for s in sources}))
        )
        return list(result.scalars())

    async def get_tags_for_channels(
        self, channel_ids: List[int], *, include_abyss: bool = True
    ) -> Sequence[Tag]:
        """获取指定频道列表内的所有唯一标签"""
        statement = (
            select(Tag)
            .join(Thread, Tag.threads)  # type: ignore
            .where(cast(ColumnElement, Thread.channel_id).in_(channel_ids))
            .distinct()
        )
        if not include_abyss:
            statement = statement.where(Tag.is_abyss.is_(False))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_all_tags(self) -> Sequence[Tag]:
        """获取数据库中所有的标签。"""
        statement = select(Tag)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_all_unique_tags_from_indexed_threads(
        self, *, source: str | None = None, include_abyss: bool = True
    ) -> Sequence[Tag]:
        """获取所有已索引帖子中的唯一标签"""
        statement = select(Tag).join(Thread, Tag.threads).distinct()  # type: ignore
        statement = statement.where(
            Tag.deleted_at.is_(None), Tag.enabled.is_(True)
        )
        if source is not None:
            statement = statement.where(Tag.source == source)
        if not include_abyss:
            statement = statement.where(Tag.is_abyss.is_(False))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_candidate_names(
        self, *, source: str, include_abyss: bool
    ) -> list[str]:
        """读取指定来源的有效候选名称。"""
        statement = select(Tag.name).where(
            Tag.source == source,
            Tag.deleted_at.is_(None),
            Tag.enabled.is_(True),
        )
        if not include_abyss:
            statement = statement.where(Tag.is_abyss.is_(False))
        return sorted(set((await self.session.execute(statement)).scalars()))

    async def filter_candidate_names(
        self, names: Iterable[str], *, include_abyss: bool
    ) -> set[str]:
        """隐藏仅对应深渊实体的已知名称，同时保留虚拟或未知名称。"""
        names = set(names)
        if include_abyss or not names:
            return names
        rows = (
            await self.session.execute(
                select(Tag.name, Tag.is_abyss).where(
                    Tag.name.in_(names), Tag.deleted_at.is_(None)
                )
            )
        ).all()
        known = {name for name, _ in rows}
        visible = {name for name, is_abyss in rows if not is_abyss}
        return (names - known) | visible

    async def custom_names(self, names: Iterable[str]) -> set[str]:
        """返回输入中至少对应一个有效自定义实体的名称。"""
        names = set(names)
        if not names:
            return set()
        return set(
            (
                await self.session.execute(
                    select(Tag.name).where(
                        Tag.name.in_(names),
                        Tag.source == "custom",
                        Tag.deleted_at.is_(None),
                    )
                )
            ).scalars()
        )

    async def update_tag_name(self, tag_id: int, new_name: str):
        """更新指定ID的标签的名称。"""
        statement = select(Tag).where(Tag.id == tag_id)  # type: ignore
        result = await self.session.execute(statement)
        tag = result.scalars().first()
        if tag and tag.source == "custom" and tag.deleted_at is None:
            tag.name = new_name
            self.session.add(tag)
            await self.session.commit()
