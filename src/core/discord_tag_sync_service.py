from sqlalchemy import select, text, update

from core.discord_tag_source_repository import DiscordTagSourceRepository
from models import DiscordTagSource, DiscordTagSyncState, Tag, Thread
from models.tag_binding import TagBinding
from models.operation_log import OperationLog
from models.tag_notification_task import TagNotificationTask
from shared.tag_error import TagError
from shared.time_utils import utc_now


class DiscordTagSyncService:
    """按完整频道快照维护来源、标准概念和绑定，事务内统一切换。"""

    def __init__(self, session):
        """复用调用方事务。"""
        self.session = session

    async def apply(self, event):
        """应用完整快照，并返回标签池公开内容是否发生变化。"""
        await self.session.execute(text("SELECT pg_advisory_xact_lock(73902141)"))
        state = await self.session.get(DiscordTagSyncState, event.channel_id)
        if state and state.observed_at >= event.observed_at:
            return False
        if len(event.tags.values()) != len(set(event.tags.values())):
            raise TagError("duplicate_channel_name", "频道存在同名标签，无法自动归一")
        sources = list(
            (
                await self.session.execute(
                    select(DiscordTagSource).where(
                        (DiscordTagSource.channel_id == event.channel_id)
                        | DiscordTagSource.discord_tag_id.in_(event.tags)
                    )
                )
            ).scalars()
        )
        if any(s.channel_id not in (None, event.channel_id) for s in sources):
            raise TagError("source_channel_conflict", "DC 来源频道不一致")
        old_tags = {s.tag_id for s in sources}
        original = {s.id: (s.tag_id, s.deleted_at) for s in sources}
        # 同步时间不进入公开响应，只比较会改变标签池投影的来源字段。
        pool_original = {
            s.id: (s.tag_id, s.channel_id, s.name, s.deleted_at) for s in sources
        }
        # 暂时释放本频道有效来源唯一键，支持一次快照内多标签改名和名称交换。
        for source in sources:
            source.deleted_at = event.observed_at
        await self.session.flush()
        concepts = await DiscordTagSourceRepository(self.session).concepts(
            event.tags.values()
        )
        by_discord = {source.discord_tag_id: source for source in sources}
        for dc_id, name in event.tags.items():
            source = by_discord.get(dc_id)
            if source is None:
                source = DiscordTagSource(
                    discord_tag_id=dc_id, name=name, tag_id=concepts[name].id
                )
                self.session.add(source)
                sources.append(source)
            source.channel_id = event.channel_id
            source.name, source.tag_id = name, concepts[name].id
            source.synced_at, source.deleted_at = event.observed_at, None
        for source in sources:
            if source.deleted_at is not None:
                source.deleted_at = original[source.id][1] or event.observed_at
                source.synced_at = event.observed_at
        await self.session.flush()
        by_id = {s.id: s for s in sources}
        bindings = list(
            (
                await self.session.execute(
                    select(TagBinding).where(
                        TagBinding.discord_source_id.in_(by_id),
                        TagBinding.ended_at.is_(None),
                        TagBinding.binding_source == "discord_sync",
                    )
                )
            ).scalars()
        )
        renamed = []
        affected = set()
        for binding in bindings:
            source = by_id[binding.discord_source_id]
            if source.deleted_at is not None:
                self.session.add(
                    OperationLog(
                        type="tag.binding.convert",
                        target_type="thread",
                        target_id=binding.target_id,
                        tag_id=binding.tag_id,
                        detail={
                            "binding_id": str(binding.id),
                            "discord_source_id": str(source.id),
                            "tag_name": source.name,
                            "target_id_kind": "internal",
                        },
                    )
                )
                binding.binding_source, binding.discord_source_id = "local", None
                affected.add(binding.target_id)
            elif binding.tag_id != source.tag_id:
                binding.ended_at, binding.end_reason = utc_now(), "discord_rename"
                renamed.append((binding.target_id, source))
                affected.add(binding.target_id)
        await self.session.flush()
        # 统一结束改名旧轮次后再处理新目标，避免名称交换产生中间冲突。
        affected_ids = sorted(affected)
        if renamed:
            current = {}
            # 大频道分批读取，避免一次 IN 参数超过 PostgreSQL 驱动上限。
            for offset in range(0, len(affected_ids), 10000):
                rows = (
                    await self.session.execute(
                        select(TagBinding).where(
                            TagBinding.target_type == "thread",
                            TagBinding.target_id.in_(
                                affected_ids[offset : offset + 10000]
                            ),
                            TagBinding.ended_at.is_(None),
                        )
                    )
                ).scalars()
                current.update({(b.target_id, b.tag_id): b for b in rows})
            for target_id, source in renamed:
                existing = current.get((target_id, source.tag_id))
                if existing:
                    if existing.binding_source == "discord_sync":
                        raise TagError(
                            "source_binding_conflict", "标准标签已有其他同步来源"
                        )
                    existing.ended_at, existing.end_reason = (
                        utc_now(),
                        "discord_takeover",
                    )
            await self.session.flush()
            for target_id, source in renamed:
                self.session.add(
                    TagBinding(
                        target_type="thread",
                        target_id=target_id,
                        tag_id=source.tag_id,
                        binding_source="discord_sync",
                        discord_source_id=source.id,
                    )
                )
        for offset in range(0, len(affected_ids), 10000):
            await self.session.execute(
                update(Thread)
                .where(Thread.id.in_(affected_ids[offset : offset + 10000]))
                .values(native_tag_revision=Thread.native_tag_revision + 1)
            )
        await self.session.flush()
        # 没有有效来源的旧概念转为自定义；分类冲突降为未分类，不阻塞同步。
        live_ids = set(
            (
                await self.session.execute(
                    select(DiscordTagSource.tag_id).where(
                        DiscordTagSource.tag_id.in_(old_tags),
                        DiscordTagSource.deleted_at.is_(None),
                    )
                )
            ).scalars()
        )
        lost = list(
            (
                await self.session.execute(
                    select(Tag).where(
                        Tag.id.in_(old_tags - live_ids),
                        Tag.source == "discord",
                        Tag.deleted_at.is_(None),
                    )
                )
            ).scalars()
        )
        custom = {
            (t.name, t.category): t.id
            for t in (
                await self.session.execute(
                    select(Tag).where(
                        Tag.source == "custom", Tag.name.in_([t.name for t in lost])
                    )
                )
            ).scalars()
        }
        for tag in lost:
            old_category = tag.category
            conflict = (
                custom.get((tag.name, tag.category))
                if tag.category is not None
                else None
            )
            if conflict:
                tag.category = None
            tag.source, tag.originated_from_discord = "custom", True
            if tag.category is None:
                self.session.add(TagNotificationTask(kind="converted", tag_id=tag.id))
            self.session.add(
                OperationLog(
                    type="tag.pool.convert",
                    target_type="tag",
                    target_id=tag.id,
                    tag_id=tag.id,
                    detail={
                        "tag_name": tag.name,
                        "previous_category": old_category,
                        "conflict_tag_id": str(conflict) if conflict else None,
                        "target_id_kind": "internal",
                    },
                )
            )
        # 来源变化留存快照，历史审计不随映射修改。
        for source in sources:
            before = original.get(source.id)
            if before is None or before != (source.tag_id, source.deleted_at):
                self.session.add(
                    OperationLog(
                        type="tag.source.sync",
                        target_type="tag",
                        target_id=source.tag_id,
                        tag_id=source.tag_id,
                        detail={
                            "discord_tag_id": str(source.discord_tag_id),
                            "channel_id": str(event.channel_id),
                            "name": source.name,
                            "before_tag_id": str(before[0]) if before else None,
                            "deleted": source.deleted_at is not None,
                            "target_id_kind": "internal",
                        },
                    )
                )
        if state:
            state.observed_at = event.observed_at
        else:
            self.session.add(
                DiscordTagSyncState(
                    channel_id=event.channel_id, observed_at=event.observed_at
                )
            )
        await self.session.flush()
        pool_current = {
            s.id: (s.tag_id, s.channel_id, s.name, s.deleted_at) for s in sources
        }
        return pool_current != pool_original
