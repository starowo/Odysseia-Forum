import hashlib
import json

from sqlalchemy import delete, select, update, literal
from sqlalchemy.dialects.postgresql import insert

from models import DiscordTagSource, Tag
from models.tag_alias import TagAlias
from models.tag_binding import TagBinding
from models.tag_relation import TagRelation
from models.tag_proposal import TagProposal
from models.tag_proposal_block import TagProposalBlock
from models.tag_notification_task import TagNotificationTask
from models.operation_log import OperationLog
from shared.tag_error import TagError
from shared.tag_rules import validate_graph
from shared.time_utils import utc_now


class TagMergeService:
    """在调用方池维护锁和事务内预检、合并概念，历史轮次不改写。"""

    def __init__(self, session):
        """复用当前事务。"""
        self.session = session

    async def inspect(self, source_id, target_id):
        """批量读取全部依赖并生成与当前状态绑定的确认版本。"""
        ids = {source_id, target_id}
        tags = list(
            (await self.session.execute(select(Tag).where(Tag.id.in_(ids)))).scalars()
        )
        by_id = {t.id: t for t in tags}
        if len(tags) != 2 or any(t.deleted_at for t in tags):
            raise TagError("tags_changed", "标签已发生变化，请刷新后重试")
        source, target = by_id[source_id], by_id[target_id]
        data = {}
        for key, model, condition in [
            ("sources", DiscordTagSource, DiscordTagSource.tag_id.in_(ids)),
            (
                "bindings",
                TagBinding,
                TagBinding.tag_id.in_(ids) & TagBinding.ended_at.is_(None),
            ),
            ("aliases", TagAlias, TagAlias.tag_id.in_(ids)),
            ("relations", TagRelation, True),
            (
                "proposals",
                TagProposal,
                TagProposal.tag_id.in_(ids) & (TagProposal.status == "pending"),
            ),
            ("blocks", TagProposalBlock, TagProposalBlock.tag_id.in_(ids)),
        ]:
            data[key] = list(
                (await self.session.execute(select(model).where(condition))).scalars()
            )
        conflicts = []
        if source.name != target.name:
            conflicts.append("仅允许标准名完全相同的标签合并")
        if source.source == "discord" and target.source != "discord":
            conflicts.append("包含 DC 概念时必须保留 DC 目标标签")
        source_channels = {
            s.channel_id
            for s in data["sources"]
            if s.tag_id == source_id
            and s.deleted_at is None
            and s.channel_id is not None
        }
        target_channels = {
            s.channel_id
            for s in data["sources"]
            if s.tag_id == target_id
            and s.deleted_at is None
            and s.channel_id is not None
        }
        if source_channels & target_channels:
            conflicts.append("同一频道不能有多个有效 DC 来源映射到同一概念")
        edges = set()
        for r in data["relations"]:
            a = target_id if r.source_id == source_id else r.source_id
            b = target_id if r.target_id == source_id else r.target_id
            if r.kind == "excludes":
                a, b = sorted((a, b))
            if a == b:
                conflicts.append("合并产生标签关系自环，请先处理关系")
            edges.add((a, b, r.kind))
        try:
            validate_graph([(a, b) for a, b, k in edges if k == "implies"])
        except TagError as exc:
            conflicts.append(exc.detail["message"])
        # 汇总票数和申请状态参与版本，预检后发生操作必须重新确认。
        fingerprint = {
            key: sorted(
                [row.model_dump(mode="json") for row in rows],
                key=lambda x: json.dumps(x, sort_keys=True),
            )
            for key, rows in data.items()
        }
        fingerprint["tags"] = [
            t.model_dump(mode="json") for t in sorted(tags, key=lambda t: t.id)
        ]
        version = hashlib.sha256(
            json.dumps(fingerprint, sort_keys=True).encode()
        ).hexdigest()
        preview = {
            "source_tag_id": str(source_id),
            "target_tag_id": str(target_id),
            "source_name": source.name,
            "target_name": target.name,
            "source_is_abyss": source.is_abyss,
            "target_is_abyss": target.is_abyss,
            "version": version,
            "can_merge": not conflicts,
            "conflicts": sorted(set(conflicts)),
            "binding_count": sum(b.tag_id == source_id for b in data["bindings"]),
            "proposal_count": sum(p.tag_id == source_id for p in data["proposals"]),
            "relation_count": sum(
                r.source_id == source_id or r.target_id == source_id
                for r in data["relations"]
            ),
        }
        return preview, source, target, data, edges

    async def execute(self, source_id, target_id, version, actor):
        """保持目标轮次、继承限制并软删除旧概念，不保存跳转字段。"""
        preview, source, target, data, edges = await self.inspect(source_id, target_id)
        if preview["version"] != version:
            raise TagError("stale_merge", "合并涉及的数据已变化，请刷新预检后重试")
        if preview["conflicts"]:
            raise TagError(
                "merge_conflict", "合并存在冲突", conflicts=preview["conflicts"]
            )
        now = utc_now()
        destinations = {
            (b.target_type, b.target_id): b
            for b in data["bindings"]
            if b.tag_id == target_id
        }
        additions = []
        mapping = []
        for old in data["bindings"]:
            if old.tag_id != source_id:
                continue
            existing = destinations.get((old.target_type, old.target_id))
            old.ended_at, old.end_reason = now, "tag_merged"
            if (
                old.binding_source == "discord_sync"
                and existing
                and existing.binding_source == "local"
            ):
                existing.ended_at, existing.end_reason = now, "discord_takeover"
                existing = None
            if existing is None:
                existing = TagBinding(
                    target_type=old.target_type,
                    target_id=old.target_id,
                    tag_id=target_id,
                    binding_source=old.binding_source,
                    discord_source_id=old.discord_source_id,
                    actor_id=actor,
                )
                additions.append(existing)
            mapping.append((old, existing))
        await self.session.flush()
        self.session.add_all(additions)
        # 来源和别名迁移不覆盖目标值，重复数据去重。
        for s in data["sources"]:
            if s.tag_id == source_id:
                s.tag_id = target_id
        await self.session.execute(
            insert(TagAlias)
            .from_select(
                ["tag_id", "name"],
                select(literal(target_id), TagAlias.name).where(
                    TagAlias.tag_id == source_id
                ),
            )
            .on_conflict_do_nothing()
        )
        await self.session.execute(delete(TagAlias).where(TagAlias.tag_id == source_id))
        await self.session.execute(
            delete(TagRelation).where(
                (TagRelation.source_id == source_id)
                | (TagRelation.target_id == source_id)
            )
        )
        # 关系分批写入，避免大标签池超出驱动参数数量限制。
        edge_rows = [
            {"source_id": a, "target_id": b, "kind": k} for a, b, k in sorted(edges)
        ]
        for offset in range(0, len(edge_rows), 1000):
            await self.session.execute(
                insert(TagRelation)
                .values(edge_rows[offset : offset + 1000])
                .on_conflict_do_nothing()
            )
        await self.session.execute(
            insert(TagProposalBlock)
            .from_select(
                ["target_type", "target_id", "tag_id", "created_at"],
                select(
                    TagProposalBlock.target_type,
                    TagProposalBlock.target_id,
                    literal(target_id),
                    TagProposalBlock.created_at,
                ).where(TagProposalBlock.tag_id == source_id),
            )
            .on_conflict_do_nothing()
        )
        # 原限制记录也保留，历史申请不会因合并失去依据。
        blocked_targets = {(b.target_type, b.target_id) for b in data["blocks"]}
        bound_targets = {(b.target_type, b.target_id) for b in data["bindings"]}
        cancelled = []
        for p in data["proposals"]:
            if (
                p.tag_id == source_id
                or (p.target_type, p.target_id) in blocked_targets
                or (p.target_type, p.target_id) in bound_targets
                or not target.enabled
                or (p.target_type == "thread" and target.source == "discord")
            ):
                p.status, p.reason, p.resolved_at = (
                    "failed",
                    "tag_merged" if p.tag_id == source_id else "tags_changed",
                    now,
                )
                cancelled.append(p.id)
        for offset in range(0, len(cancelled), 10000):
            await self.session.execute(
                update(TagNotificationTask)
                .where(
                    TagNotificationTask.proposal_id.in_(
                        cancelled[offset : offset + 10000]
                    ),
                    TagNotificationTask.status == "pending",
                )
                .values(status="cancelled")
            )
        source.deleted_at, source.enabled = now, False
        target.originated_from_discord |= source.originated_from_discord
        await self.session.flush()
        # 每个改动轮次记录前后 ID，旧轮次和投票本身不改写。
        for old, new in mapping:
            self.session.add(
                OperationLog(
                    type="tag.binding.merge",
                    actor_id=actor,
                    target_type=old.target_type,
                    target_id=old.target_id,
                    tag_id=target_id,
                    detail={
                        "source_tag_id": str(source_id),
                        "target_tag_id": str(target_id),
                        "old_binding_id": str(old.id),
                        "new_binding_id": str(new.id),
                        "tag_name": target.name,
                        "target_id_kind": "internal",
                    },
                )
            )
        self.session.add(
            OperationLog(
                type="tag.pool.merge",
                actor_id=actor,
                target_type="tag",
                target_id=source_id,
                tag_id=source_id,
                detail={**preview, "target_id_kind": "internal"},
            )
        )
        return target
