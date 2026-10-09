import hashlib
import unicodedata
from datetime import timedelta

from sqlalchemy import func, or_, select, text

from core.tag_access_service import TagAccessService
from core.tag_data_repository import TagDataRepository
from core.tag_merge_service import TagMergeService
from core.tag_presentation import load_discord_sources, tag_data
from models import Booklist, Tag, Thread
from models.operation_log import OperationLog
from models.tag_alias import TagAlias
from models.tag_binding import TagBinding
from models.tag_notification_task import TagNotificationTask
from models.tag_proposal import TagProposal
from models.tag_proposal_block import TagProposalBlock
from models.tag_relation import TagRelation
from models.tag_vote import TagVote
from shared.tag_description import normalize_tag_description
from shared.tag_error import TagError
from shared.tag_rules import validate_graph, validate_selection
from shared.time_utils import utc_now


class CustomTagService:
    """协调标签池、绑定、审核和投票的完整数据库事务。"""

    def __init__(self, session, config, access=None):
        self.session = session
        self.access = access or TagAccessService(config)
        self.tag_cache = {}
        self.source_cache = {}

    def repo(self, model):
        """获取当前事务内的单表仓储。"""
        return TagDataRepository(self.session, model)

    def tag_data(self, tag):
        """返回已批量加载来源的标准概念。"""
        return tag_data(tag, self.source_cache)

    async def merge(self, actor, payload):
        """仅 BOT 管理员预检或执行同名概念合并。"""
        if not self.access.bot_admin(actor):
            raise TagError("forbidden", "仅 BOT 管理员可合并标签", 403)
        service = TagMergeService(self.session)
        source_id, target_id = int(payload["tag_id"]), int(payload["target_tag_id"])
        if payload.get("preview"):
            return (await service.inspect(source_id, target_id))[0]
        tag = await service.execute(source_id, target_id, payload["version"], actor)
        self.source_cache.update(await load_discord_sources(self.session, [tag.id]))
        return self.tag_data(tag)

    async def dispatch(self, command):
        """执行白名单事件命令，事务由入口统一提交。"""
        handlers = {
            "pool": self.pool,
            "manage": self.manage,
            "merge": self.merge,
            "relations": self.relations,
            "read": self.read,
            "replace": self.replace,
            "propose": self.propose,
            "proposals": self.proposals,
            "review": self.review,
            "vote": self.vote,
            "audit": self.audit,
        }
        if command.action not in handlers:
            raise TagError("unknown_command", "未知标签操作", 400)
        # 池维护与绑定写入互斥，防止软删除和新增绑定交错。
        exclusive = command.action in ("manage", "merge")
        lock = "pg_advisory_xact_lock" if exclusive else "pg_advisory_xact_lock_shared"
        await self.session.execute(text(f"SELECT {lock}(73902141)"))
        return await handlers[command.action](command.actor_id, command.payload)

    async def log(self, action, actor, kind, target_id, tag_id=None, **detail):
        """在业务事务中保存可追溯的操作快照。"""
        if tag_id is not None:
            tag = self.tag_cache.get(tag_id) or await self.session.get(Tag, tag_id)
            if tag:
                detail["tag_name"] = tag.name
                detail["category"] = tag.category
        detail["target_id_kind"] = "internal"
        await self.repo(OperationLog).add(
            type=action,
            actor_id=actor,
            target_type=kind,
            target_id=target_id,
            tag_id=tag_id,
            detail=detail,
        )

    async def target(self, actor, payload, manage=False, audit=False):
        """锁定目标并检查当前访问权限。"""
        kind, target_id = payload["target_type"], int(payload["target_id"])
        if kind not in ("thread", "booklist"):
            raise TagError("invalid_target", "目标类型无效", 422)
        model = Thread if kind == "thread" else Booklist
        key = (
            (Thread.id if payload.get("_internal_target") else Thread.thread_id)
            if kind == "thread"
            else Booklist.id
        )
        target = await self.repo(model).one(key == target_id, lock=True)
        if target is None:
            raise TagError("not_found", "目标不存在", 404)
        allowed = await self.access.access(
            actor, kind, target, manage=manage, audit=audit
        )
        return kind, target.id, target, allowed

    async def bindings(self, kind, target_id):
        """读取目标的全部生效绑定轮次。"""
        rows = await self.repo(TagBinding).rows(
            TagBinding.target_type == kind,
            TagBinding.target_id == target_id,
            TagBinding.ended_at.is_(None),
            TagBinding.binding_source == "local",
        )
        return {b.tag_id: b for b in rows}

    async def native_tags(self, kind, target):
        """按内部帖子主键读取原生标签。"""
        if kind != "thread":
            return []
        statement = (
            select(Tag)
            .join(TagBinding, Tag.id == TagBinding.tag_id)
            .where(
                TagBinding.target_type == "thread",
                TagBinding.target_id == target.id,
                TagBinding.binding_source == "discord_sync",
                TagBinding.ended_at.is_(None),
                Tag.deleted_at.is_(None),
                Tag.source == "discord",
            )
        )
        return list((await self.session.execute(statement)).scalars())

    async def snapshot(self, actor, kind, target_id, target):
        """批量生成目标标签快照与并发版本。"""
        bindings = await self.bindings(kind, target_id)
        native = await self.native_tags(kind, target)
        tags = await self.repo(Tag).rows(Tag.id.in_(bindings), Tag.deleted_at.is_(None))
        self.tag_cache.update({tag.id: tag for tag in tags})
        self.source_cache.update(
            await load_discord_sources(self.session, [t.id for t in tags + native])
        )
        native_bindings = await self.repo(TagBinding).rows(
            TagBinding.target_type == kind,
            TagBinding.target_id == target_id,
            TagBinding.binding_source == "discord_sync",
            TagBinding.ended_at.is_(None),
        )
        native_source = {b.tag_id: str(b.discord_source_id) for b in native_bindings}
        votes = await self.repo(TagVote).rows(
            TagVote.binding_id.in_([b.id for b in bindings.values()]),
            TagVote.user_id == actor,
        )
        mine = {v.binding_id: v.vote for v in votes}
        version_data = sorted(
            [f"n:{t.id}" for t in native] + [f"c:{b.id}" for b in bindings.values()]
        )
        history = (
            await self.session.execute(
                select(
                    func.max(TagBinding.id),
                    func.max(TagBinding.created_at),
                    func.max(TagBinding.ended_at),
                ).where(
                    TagBinding.target_type == kind,
                    TagBinding.target_id == target_id,
                )
            )
        ).one()
        version_data.append(str(tuple(history)))
        version_data.append(str(getattr(target, "native_tag_revision", 0)))
        result = [
            dict(
                self.tag_data(t),
                readonly=True,
                binding_source="discord_sync",
                discord_source_id=native_source[t.id],
            )
            for t in native
        ]
        for tag in tags:
            binding = bindings[tag.id]
            result.append(
                dict(
                    self.tag_data(tag),
                    readonly=False,
                    binding_source="local",
                    binding_id=str(binding.id),
                    upvotes=binding.upvotes,
                    downvotes=binding.downvotes,
                    my_vote=mine.get(binding.id, 0),
                )
            )
        all_ids = {t.id for t in tags + native}
        conflicts = await self.repo(TagRelation).rows(
            TagRelation.kind == "excludes",
            TagRelation.source_id.in_(all_ids),
            TagRelation.target_id.in_(all_ids),
        )
        return {
            "over_limit": len(all_ids) > 12,
            "conflicting_pairs": [
                [str(r.source_id), str(r.target_id)] for r in conflicts
            ],
            "version": hashlib.sha256("|".join(version_data).encode()).hexdigest(),
            "tags": result,
        }

    async def read(self, actor, payload):
        """读取目标标签，不披露其他用户身份。"""
        kind, tid, target, _ = await self.target(actor, payload)
        return await self.snapshot(actor, kind, tid, target)

    async def validate(self, kind, target, current, desired):
        """验证目标最终集合，不计算包含关系。"""
        tags = await self.repo(Tag).rows(Tag.id.in_(desired))
        if len(tags) != len(desired) or any(t.deleted_at for t in tags):
            raise TagError("tags_changed", "标签已发生变化，请刷新后重试")
        self.tag_cache.update({tag.id: tag for tag in tags})
        native = await self.native_tags(kind, target)
        native_ids = {t.id for t in native}
        if desired & native_ids:
            raise TagError("readonly_tag", "DC 同步绑定不可通过索引页修改", 403)
        relations = await self.repo(TagRelation).rows(TagRelation.kind == "excludes")
        eligible = {
            t.id: t
            for t in tags
            if kind != "thread" or t.source == "custom" or t.id in current
        }
        validate_selection(
            set(current),
            desired,
            len(native),
            eligible,
            [(r.source_id, r.target_id) for r in relations],
        )
        if desired - set(current):
            combined = desired | native_ids
            pairs = [
                [str(r.source_id), str(r.target_id)]
                for r in relations
                if r.source_id in combined and r.target_id in combined
            ]
            if pairs:
                raise TagError("tag_conflict", "目标标签存在互斥关系", pairs=pairs)

    async def end(self, binding, actor, reason):
        """结束当前挂标轮次，保留投票明细和审计。"""
        binding.ended_at = utc_now()
        binding.end_reason = reason
        await self.log(
            "tag.unbind",
            actor,
            binding.target_type,
            binding.target_id,
            binding.tag_id,
            binding_id=str(binding.id),
            reason=reason,
            upvotes=binding.upvotes,
            downvotes=binding.downvotes,
        )

    async def attach(self, actor, kind, tid, tag_id, reason):
        """建立新的零票绑定并完成同标签待审核项。"""
        binding = await self.repo(TagBinding).add(
            target_type=kind,
            target_id=tid,
            tag_id=tag_id,
            actor_id=actor,
        )
        await self.log(
            "tag.bind",
            actor,
            kind,
            tid,
            tag_id,
            binding_id=str(binding.id),
            reason=reason,
        )
        pending = await self.repo(TagProposal).rows(
            TagProposal.target_type == kind,
            TagProposal.target_id == tid,
            TagProposal.tag_id == tag_id,
            TagProposal.status == "pending",
        )
        for proposal in pending:
            proposal.status, proposal.reason, proposal.resolved_at = (
                "approved",
                reason,
                utc_now(),
            )
        return binding

    async def replace(self, actor, payload):
        """按目标集合替换，保留交集轮次和票数。"""
        kind, tid, target, _ = await self.target(actor, payload, manage=True)
        snapshot = await self.snapshot(actor, kind, tid, target)
        if payload["version"] != snapshot["version"]:
            raise TagError("stale_version", "标签已变化，请刷新后重试")
        current = await self.bindings(kind, tid)
        desired = {int(v) for v in payload["tag_ids"]}
        await self.validate(kind, target, current, desired)
        for tag_id in set(current) - desired:
            await self.end(current[tag_id], actor, "manual")
        for tag_id in desired - set(current):
            await self.attach(actor, kind, tid, tag_id, "manual")
        await self.session.flush()
        return await self.snapshot(actor, kind, tid, target)

    async def blocked(self, kind, tid, tag_id):
        """判断是否曾被投票移除。"""
        return await self.repo(TagProposalBlock).one(
            TagProposalBlock.target_type == kind,
            TagProposalBlock.target_id == tid,
            TagProposalBlock.tag_id == tag_id,
        )

    async def propose(self, actor, payload):
        """新增非公开的单标签审核申请。"""
        kind, tid, target, _ = await self.target(actor, payload)
        tag_id = int(payload["tag_id"])
        if await self.blocked(kind, tid, tag_id):
            raise TagError("proposal_blocked", "此标签曾被投票移除，不能再次提议")
        current = await self.bindings(kind, tid)
        if tag_id in current:
            raise TagError("already_bound", "标签已存在")
        await self.validate(kind, target, current, set(current) | {tag_id})
        pending = await self.repo(TagProposal).one(
            TagProposal.target_type == kind,
            TagProposal.target_id == tid,
            TagProposal.tag_id == tag_id,
            TagProposal.status == "pending",
        )
        if pending:
            raise TagError("already_pending", "此标签已有待审核申请")
        proposal = await self.repo(TagProposal).add(
            target_type=kind,
            target_id=tid,
            tag_id=tag_id,
            applicant_id=actor,
            owner_id=target.author_id if kind == "thread" else target.owner_id,
            due_at=utc_now() + timedelta(days=7),
        )
        await self.repo(TagNotificationTask).add(proposal_id=proposal.id)
        await self.log(
            "tag.propose", actor, kind, tid, tag_id, proposal_id=str(proposal.id)
        )
        return await self.proposal_data(proposal)

    async def proposal_data(self, proposal):
        """输出不含其他用户身份的提议状态。"""
        tag = self.tag_cache.get(proposal.tag_id) or await self.session.get(
            Tag, proposal.tag_id
        )
        return {
            "id": str(proposal.id),
            "tag_name": tag.name if tag else "已删除标签",
            "tag_id": str(proposal.tag_id),
            "is_abyss": tag.is_abyss if tag else False,
            "status": proposal.status,
            "reason": proposal.reason,
            "created_at": proposal.created_at,
            "due_at": proposal.due_at,
            "resolved_at": proposal.resolved_at,
        }

    async def proposals(self, actor, payload):
        """提供作者审核队列或申请人自己的申请历史。"""
        kind, tid, _, allowed = await self.target(actor, payload)
        conditions = [TagProposal.target_type == kind, TagProposal.target_id == tid]
        if payload.get("review_queue"):
            if not allowed:
                raise TagError("forbidden", "无审核权限", 403)
            conditions.append(TagProposal.status == "pending")
        else:
            conditions.append(TagProposal.applicant_id == actor)
        statement = (
            select(TagProposal)
            .where(*conditions)
            .order_by(TagProposal.id.desc())
            .limit(100)
            .offset(payload.get("offset", 0))
        )
        proposals = list((await self.session.execute(statement)).scalars())
        tags = await self.repo(Tag).rows(Tag.id.in_({p.tag_id for p in proposals}))
        self.tag_cache.update({tag.id: tag for tag in tags})
        return [await self.proposal_data(p) for p in proposals]

    async def resolve(
        self, actor, proposal, kind, tid, target, approve, automatic=False
    ):
        """完成一次审核，校验失败也形成明确终态。"""
        if proposal.status != "pending":
            raise TagError("already_resolved", "申请已处理")
        if approve:
            try:
                current = await self.bindings(kind, tid)
                if automatic and await self.blocked(kind, tid, proposal.tag_id):
                    raise TagError("proposal_blocked", "此标签曾被投票移除")
                await self.validate(
                    kind, target, current, set(current) | {proposal.tag_id}
                )
                if proposal.tag_id not in current:
                    await self.attach(
                        actor,
                        kind,
                        tid,
                        proposal.tag_id,
                        "timeout" if automatic else "review",
                    )
                proposal.status, proposal.reason = (
                    "approved",
                    "timeout" if automatic else "review",
                )
            except TagError as exc:
                proposal.status, proposal.reason = "failed", exc.detail["code"]
        else:
            proposal.status, proposal.reason = "rejected", "review"
        proposal.resolved_at = utc_now()
        await self.log(
            "tag.review",
            actor or None,
            kind,
            tid,
            proposal.tag_id,
            proposal_id=str(proposal.id),
            status=proposal.status,
            reason=proposal.reason,
        )
        return await self.proposal_data(proposal)

    async def review(self, actor, payload):
        """作者或管理组审核指定目标上的申请。"""
        kind, tid, target, _ = await self.target(actor, payload, manage=True)
        proposal = await self.repo(TagProposal).one(
            TagProposal.id == int(payload["proposal_id"]),
            TagProposal.target_type == kind,
            TagProposal.target_id == tid,
        )
        if proposal is None:
            raise TagError("not_found", "申请不存在", 404)
        return await self.resolve(
            actor, proposal, kind, tid, target, payload["approve"]
        )

    async def vote(self, actor, payload):
        """幂等设置当前轮次投票，净负票超过五票自动下标。"""
        kind, tid, target, _ = await self.target(actor, payload)
        binding = await self.repo(TagBinding).one(
            TagBinding.id == int(payload["binding_id"]),
            TagBinding.target_type == kind,
            TagBinding.target_id == tid,
            TagBinding.ended_at.is_(None),
        )
        if binding is not None and binding.binding_source != "local":
            raise TagError("readonly_tag", "DC 原生绑定不可投票", 403)
        if binding is None:
            raise TagError("stale_binding", "挂标轮次已结束，请刷新")
        value = payload["vote"]
        if value not in (-1, 0, 1):
            raise TagError("invalid_vote", "投票必须为 -1、0 或 1", 422)
        vote = await self.repo(TagVote).one(
            TagVote.binding_id == binding.id,
            TagVote.user_id == actor,
        )
        old = vote.vote if vote else 0
        if old != value:
            binding.upvotes += int(value == 1) - int(old == 1)
            binding.downvotes += int(value == -1) - int(old == -1)
            if vote and value:
                vote.vote = value
            elif vote:
                await self.repo(TagVote).remove(vote)
            elif value:
                await self.repo(TagVote).add(
                    binding_id=binding.id, user_id=actor, vote=value
                )
            await self.log(
                "tag.vote",
                actor,
                kind,
                tid,
                binding.tag_id,
                binding_id=str(binding.id),
                before=old,
                after=value,
            )
            if binding.downvotes - binding.upvotes > 5:
                await self.end(binding, actor, "downvote")
                if not await self.blocked(kind, tid, binding.tag_id):
                    await self.repo(TagProposalBlock).add(
                        target_type=kind, target_id=tid, tag_id=binding.tag_id
                    )
        await self.session.flush()
        return await self.snapshot(actor, kind, tid, target)

    async def pool(self, actor, payload):
        """搜索标准名与别名，默认仅列出可选标签。"""
        conditions = []
        if not payload.get("_can_view_abyss", False):
            conditions.append(Tag.is_abyss.is_(False))
        # 按实体当前来源筛选后再分页，转换标签仍属于自定义标签。
        if source := payload.get("source"):
            conditions.append(Tag.source == source)
        if payload.get("include_deleted"):
            if not self.access.bot_admin(actor):
                raise TagError("forbidden", "仅 BOT 管理员可查询已删除标签", 403)
        else:
            conditions.append(Tag.deleted_at.is_(None))
        if payload.get("selectable", True):
            conditions.append(Tag.enabled.is_(True))
        if payload.get("category"):
            conditions.append(Tag.category == payload["category"])
        if query := payload.get("q"):
            pattern = (
                "%"
                + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                + "%"
            )
            aliases = select(TagAlias.tag_id).where(TagAlias.name.ilike(pattern))
            conditions.append(or_(Tag.name.ilike(pattern), Tag.id.in_(aliases)))
        statement = (
            select(Tag)
            .where(*conditions)
            .order_by(Tag.category, Tag.name, Tag.id)
        )
        tags = list((await self.session.execute(statement)).scalars())
        self.source_cache.update(
            await load_discord_sources(self.session, [t.id for t in tags])
        )
        aliases = await self.repo(TagAlias).rows(
            TagAlias.tag_id.in_([t.id for t in tags])
        )
        grouped = {}
        for alias in aliases:
            grouped.setdefault(alias.tag_id, []).append(alias.name)
        return [
            dict(self.tag_data(t), aliases=sorted(grouped.get(t.id, []))) for t in tags
        ]

    async def relations(self, actor, payload):
        """返回未删除标签间的直接关系，不计算传递闭包。"""
        active_conditions = [Tag.deleted_at.is_(None)]
        if not payload.get("_can_view_abyss", False):
            active_conditions.append(Tag.is_abyss.is_(False))
        active = select(Tag.id).where(*active_conditions)
        rows = await self.repo(TagRelation).rows(
            TagRelation.source_id.in_(active), TagRelation.target_id.in_(active)
        )
        return [
            {
                "source_id": str(r.source_id),
                "target_id": str(r.target_id),
                "kind": r.kind,
            }
            for r in rows
        ]

    async def manage(self, actor, payload):
        """维护标签实体及辅助数据，保留所有历史唯一性。"""
        if not self.access.bot_admin(actor):
            raise TagError("forbidden", "仅 BOT 管理员可维护标签池", 403)
        action = payload["operation"]
        tag = None
        if payload.get("tag_id"):
            tag = await self.repo(Tag).one(Tag.id == int(payload["tag_id"]), lock=True)
            if tag is None:
                raise TagError("not_found", "标签不存在", 404)
        if action == "classify":
            if (
                tag is None
                or not tag.originated_from_discord
                or tag.category is not None
                or tag.deleted_at
            ):
                raise TagError("already_classified", "标签已分类或不可处理")
            action = "update"
        if tag is not None and tag.deleted_at and action != "restore":
            raise TagError("tags_changed", "标签已发生变化，请刷新后重试")
        if tag is not None and action == "restore":
            merged = await self.repo(OperationLog).one(
                OperationLog.type == "tag.pool.merge", OperationLog.target_id == tag.id
            )
            if merged:
                raise TagError(
                    "tags_changed", "已合并标签不可恢复，请刷新后选择当前标签"
                )
        if tag is not None and tag.source == "discord":
            if action in ("delete", "restore") or (
                "name" in payload and payload["name"] != tag.name
            ):
                raise TagError(
                    "dc_concept_readonly",
                    "DC 标准概念不可改名或删除，可维护分类、别名、关系及启用状态",
                    403,
                )
        if tag is not None:
            self.tag_cache[tag.id] = tag
        before = (
            {
                "name": tag.name,
                "description": tag.description,
                "is_abyss": tag.is_abyss,
                "category": tag.category,
                "enabled": tag.enabled,
                "deleted": bool(tag.deleted_at),
            }
            if tag
            else None
        )
        if action in ("create", "update"):
            description = normalize_tag_description(
                payload.get("description", tag.description if tag else "")
            )
            is_abyss = payload.get("is_abyss", tag.is_abyss if tag else False)
            if not isinstance(is_abyss, bool):
                raise TagError(
                    "invalid_is_abyss", "深渊向标识必须为布尔值", 422
                )
            if action == "update" and tag is None:
                raise TagError("missing_tag", "修改必须提供标签 ID", 422)
            name = unicodedata.normalize(
                "NFC", payload.get("name", tag.name if tag else "")
            ).strip()
            if tag is not None and tag.source == "discord":
                name = tag.name
            category = payload.get("category", tag.category if tag else None)
            if (
                not name
                or len(name) > 100
                or (
                    category not in range(1, 8)
                    and not (
                        tag
                        and (tag.originated_from_discord or tag.source == "discord")
                        and category is None
                    )
                )
            ):
                raise TagError(
                    "invalid_tag", "名称须为 1 至 100 字且分类须为 1 至 7", 422
                )
            duplicate = (
                await self.repo(Tag).one(
                    Tag.source == "custom", Tag.name == name, Tag.category == category
                )
                if category is not None and (tag is None or tag.source == "custom")
                else None
            )
            if (
                category is not None
                and duplicate
                and (tag is None or duplicate.id != tag.id)
            ):
                raise TagError(
                    "deleted_tag_exists" if duplicate.deleted_at else "tag_exists",
                    "该标签已删除，可恢复" if duplicate.deleted_at else "标签已存在",
                    tag_id=str(duplicate.id),
                    conflict_tag_id=str(tag.id)
                    if tag and (tag.originated_from_discord or tag.source == "discord")
                    else None,
                )
            if tag is None:
                tag = await self.repo(Tag).add(
                    name=name,
                    category=category,
                    source="custom",
                    description=description,
                    is_abyss=is_abyss,
                )
            else:
                tag.name, tag.category = name, category
                tag.description = description
                if "is_abyss" in payload:
                    tag.is_abyss = is_abyss
            if "enabled" in payload:
                if not isinstance(payload["enabled"], bool):
                    raise TagError("invalid_enabled", "启用状态必须为布尔值", 422)
                if tag.deleted_at:
                    raise TagError("deleted_tag", "请先恢复已删除标签")
                tag.enabled = payload["enabled"]
            if "aliases" in payload:
                for alias in await self.repo(TagAlias).rows(TagAlias.tag_id == tag.id):
                    await self.repo(TagAlias).remove(alias)
                await self.session.flush()
                for alias in sorted(
                    {
                        unicodedata.normalize("NFC", a).strip()
                        for a in payload["aliases"]
                    }
                ):
                    if not alias or len(alias) > 200:
                        raise TagError("invalid_alias", "别名须为 1 至 200 字", 422)
                    await self.repo(TagAlias).add(tag_id=tag.id, name=alias)
        elif action in ("disable", "enable", "delete", "restore"):
            if tag is None:
                raise TagError("missing_tag", "必须提供标签 ID", 422)
            if action == "disable":
                tag.enabled = False
            elif action == "enable":
                if tag.deleted_at:
                    raise TagError("deleted_tag", "请先恢复已删除标签")
                tag.enabled = True
            elif action == "restore":
                tag.deleted_at, tag.enabled = None, True
            elif not tag.deleted_at:
                tag.deleted_at = utc_now()
                for binding in await self.repo(TagBinding).rows(
                    TagBinding.tag_id == tag.id,
                    TagBinding.ended_at.is_(None),
                ):
                    await self.end(binding, actor, "tag_deleted")
                for proposal in await self.repo(TagProposal).rows(
                    TagProposal.tag_id == tag.id, TagProposal.status == "pending"
                ):
                    proposal.status, proposal.reason, proposal.resolved_at = (
                        "failed",
                        "tag_deleted",
                        utc_now(),
                    )
        elif action in ("add_relation", "remove_relation"):
            if tag is None or tag.deleted_at:
                raise TagError("missing_tag", "关系源标签不可用", 422)
            other = await self.session.get(Tag, int(payload["target_tag_id"]))
            if other is None or other.deleted_at:
                raise TagError("tags_changed", "标签已发生变化，请刷新后重试")
            kind = payload["kind"]
            if kind not in ("implies", "excludes") or tag.id == other.id:
                raise TagError("invalid_relation", "关系类型无效或存在自环", 422)
            a, b = tag.id, other.id
            if kind == "excludes":
                a, b = sorted((a, b))
            existing = await self.repo(TagRelation).one(
                TagRelation.source_id == a,
                TagRelation.target_id == b,
                TagRelation.kind == kind,
            )
            if action == "remove_relation" and existing:
                await self.repo(TagRelation).remove(existing)
            elif action == "add_relation" and not existing:
                if kind == "implies":
                    edges = await self.repo(TagRelation).rows(TagRelation.kind == kind)
                    validate_graph(
                        [(r.source_id, r.target_id) for r in edges] + [(a, b)]
                    )
                await self.repo(TagRelation).add(source_id=a, target_id=b, kind=kind)
        else:
            raise TagError("invalid_operation", "未知管理操作", 422)
        await self.log(
            "tag.pool." + action,
            actor,
            "tag",
            tag.id,
            tag.id,
            before=before,
            after={
                "name": tag.name,
                "description": tag.description,
                "is_abyss": tag.is_abyss,
                "category": tag.category,
                "enabled": tag.enabled,
                "deleted": bool(tag.deleted_at),
            },
            aliases=payload.get("aliases"),
            relation_target=payload.get("target_tag_id"),
            relation_kind=payload.get("kind"),
        )
        await self.session.flush()
        self.source_cache.update(await load_discord_sources(self.session, [tag.id]))
        return self.tag_data(tag)

    async def audit(self, actor, payload):
        """管理组在目标权限范围内分页查询审计记录。"""
        kind = payload["target_type"]
        if kind == "tag":
            if not self.access.bot_admin(actor):
                raise TagError("forbidden", "仅 BOT 管理员可查标签池审计", 403)
            tid = int(payload["target_id"])
        else:
            kind, tid, _, _ = await self.target(actor, payload, audit=True)
        statement = (
            select(OperationLog)
            .where(
                OperationLog.target_type == kind,
                OperationLog.target_id == tid,
            )
            .order_by(OperationLog.id.desc())
            .offset(payload.get("offset", 0))
            .limit(100)
        )
        return [
            {
                "id": str(r.id),
                "type": r.type,
                "actor_id": str(r.actor_id) if r.actor_id else None,
                "tag_id": str(r.tag_id) if r.tag_id else None,
                "detail": r.detail,
                "created_at": r.created_at,
            }
            for r in (await self.session.execute(statement)).scalars()
        ]
