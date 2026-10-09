from sqlalchemy import select, text

from models import DiscordTagSource, DiscordTagSyncState, Tag
from models.tag_notification_task import TagNotificationTask


class DiscordTagSourceRepository:
    """批量解析 DC 来源与标准概念；已知来源的改名和失效由完整快照处理。"""

    def __init__(self, session):
        """复用当前事务。"""
        self.session = session

    async def concepts(self, names):
        """同名 DC 概念唯一，避免通过重复 INSERT 消耗序列。"""
        names = set(names)
        if not names:
            return {}
        rows = list(
            (
                await self.session.execute(
                    select(Tag).where(
                        Tag.name.in_(names),
                        Tag.source == "discord",
                        Tag.deleted_at.is_(None),
                    )
                )
            ).scalars()
        )
        result = {tag.name: tag for tag in rows}
        conflicting = set(
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
        for name in sorted(names - result.keys()):
            tag = Tag(name=name, source="discord", originated_from_discord=True)
            self.session.add(tag)
            result[name] = tag
        await self.session.flush()
        for name in names - {tag.name for tag in rows}:
            if name in conflicting:
                self.session.add(
                    TagNotificationTask(kind="collision", tag_id=result[name].id)
                )
        return result

    async def ensure(self, tags_data, channel_id=None):
        """帖子快照仅补齐未知来源，不用缓存名称覆盖完整频道同步结果。"""
        if not tags_data:
            return []
        await self.session.execute(text("SELECT pg_advisory_xact_lock(73902141)"))
        existing = list(
            (
                await self.session.execute(
                    select(DiscordTagSource).where(
                        DiscordTagSource.discord_tag_id.in_(tags_data)
                    )
                )
            ).scalars()
        )
        known = {source.discord_tag_id for source in existing}
        # 已有完整频道检查点时，未知缓存标签不能绕过权威快照重新创建来源。
        missing = tags_data.keys() - known
        if channel_id is not None and await self.session.get(
            DiscordTagSyncState, channel_id
        ):
            missing = set()
        concepts = await self.concepts(tags_data[key] for key in missing)
        for key in sorted(missing):
            source = DiscordTagSource(
                discord_tag_id=key,
                channel_id=channel_id,
                name=tags_data[key],
                tag_id=concepts[tags_data[key]].id,
            )
            self.session.add(source)
            existing.append(source)
        for source in existing:
            if source.channel_id is None and channel_id is not None:
                source.channel_id = channel_id
        await self.session.flush()
        return [source for source in existing if source.deleted_at is None]
