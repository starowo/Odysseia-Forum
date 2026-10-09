import asyncio
import logging
import time
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Float, and_, case, cast, func, select

from core.tag_cache_service import TagCacheService
from core.tag_query import tag_filters, tag_name_filters, require_current_tag_ids
from core.thread_repository import ThreadRepository
from dto.preferences import UserSearchPreferencesDTO
from dto.search import (
    SearchConfigDTO,
    SimilarThreadCandidateDTO,
    SimilarThreadSourceDTO,
    SimilarThreadSourceTagDTO,
)
from models import Author, Tag, Thread, TagBinding, BooklistItem
from search.qo.cleaned_thread_search import CleanedThreadSearchQuery
from search.qo.thread_search import ThreadSearchQuery
from shared.channel_mapping_utils import ChannelMappingUtils
from shared.enum import DefaultPreferences, SearchConfigDefaults
from shared.range_parser import parse_range_string
from shared.time_parser import parse_time_string

logger = logging.getLogger(__name__)


class SearchService:
    """封装与搜索相关的数据库操作。"""

    def __init__(self, session: AsyncSession, tag_cache_service: TagCacheService):
        self.session = session
        self.tag_cache_service = tag_cache_service

    def _clean_query(
        self,
        query: ThreadSearchQuery,
        exclude_thread_ids: Sequence[int | str] | None = None,
    ) -> CleanedThreadSearchQuery:
        """
        对 ThreadSearchQuery 进行数据清洗和规范化，返回 CleanedThreadSearchQuery。

        包括：时间解析、标签 ID 解析、排除帖子 ID 规范化、
        包含作者 ID 初始化、作者名规范化。
        """
        # 解析时间字符串
        try:
            created_after_dt = parse_time_string(query.created_after)
            created_before_dt = parse_time_string(query.created_before)
            active_after_dt = parse_time_string(query.active_after)
            active_before_dt = parse_time_string(query.active_before)
        except ValueError as e:
            # 理论上不应该发生，因为在 Modal 中已经验证过
            logging.warning(f"时间字符串解析失败: {e}")
            raise

        # 解析标签 ID
        resolved_include_tag_ids = [
            id
            for name in query.include_tags
            for id in self.tag_cache_service.get_ids_by_tag_name(name)
        ]
        resolved_exclude_tag_ids = [
            id
            for name in query.exclude_tags
            for id in self.tag_cache_service.get_ids_by_tag_name(name)
        ]

        # 规范化排除帖子 ID
        normalized_exclude_thread_ids: list[int] = []
        if exclude_thread_ids:
            for tid in exclude_thread_ids:
                try:
                    normalized_exclude_thread_ids.append(int(tid))
                except (TypeError, ValueError):
                    continue

        # 初始化包含作者 ID
        final_include_author_ids = (
            set(query.include_authors) if query.include_authors else set()
        )

        # 规范化作者名
        normalized_author_name = (
            query.author_name.strip() if query.author_name else None
        )
        if normalized_author_name == "":
            normalized_author_name = None

        return CleanedThreadSearchQuery(
            query=query,
            created_after_dt=created_after_dt,
            created_before_dt=created_before_dt,
            active_after_dt=active_after_dt,
            active_before_dt=active_before_dt,
            resolved_include_tag_ids=resolved_include_tag_ids,
            resolved_exclude_tag_ids=resolved_exclude_tag_ids,
            normalized_exclude_thread_ids=normalized_exclude_thread_ids,
            final_include_author_ids=final_include_author_ids,
            normalized_author_name=normalized_author_name,
        )

    def _apply_range_filter(self, filters, column, range_str):
        """解析范围字符串并应用为SQLAlchemy过滤器"""
        min_val, max_val, min_op, max_op = parse_range_string(range_str)
        if min_val is not None and min_op is not None:
            if min_op == ">=":
                filters.append(column >= min_val)
            else:
                filters.append(column > min_val)

        if max_val is not None and max_op is not None:
            if max_op == "<=":
                filters.append(column <= max_val)
            else:
                filters.append(column < max_val)

    def _apply_ucb1_ranking(
        self,
        statement,
        total_display_count: int,
        exploration_factor: float,
        strength_weight: float,
    ):
        """
        应用 UCB1 算法对帖子进行排序。
        Score = W * (x / n) + C * sqrt(ln(N) / n)
        """
        W = strength_weight
        C = exploration_factor
        N = float(max(1, total_display_count))

        # reaction_count as x
        # display_count as n
        x = cast(Thread.reaction_count, Float)
        n = case(
            (Thread.display_count > 0, cast(Thread.display_count, Float)),
            else_=1.0,  # 避免除零，并给新帖子最大探索加成
        )

        exploitation_term = W * (x / n)
        # N/n 可能会非常大，取对数避免溢出
        exploration_term = C * func.sqrt(func.log(N) / n)

        final_score = (exploitation_term + exploration_term).label("final_score")

        return statement, final_score

    def _apply_reddit_hot_ranking(self, statement, time_decay: float):
        """
        应用 Reddit Hot 算法对帖子排序。
        Score = log10(max(1, reaction_count)) + (created_at_unix / time_decay)

        时间部分线性对新帖加成；分数部分高票帖不会获得不成比例的巨大优势。
        """
        # SQLite 不内置 log10，用 ln/ln(10) 转换确保跨后端兼容
        ln10 = 2.302585092994046
        reaction_score = (
            func.log(
                case(
                    (Thread.reaction_count > 1, cast(Thread.reaction_count, Float)),
                    else_=1.0,
                )
            )
            / ln10
        )

        # created_at 是 UTC datetime，用 extract(epoch) 转 Unix 秒（跨数据库兼容）
        time_score = func.extract("epoch", Thread.created_at).cast(Float) / float(
            time_decay
        )

        final_score = (reaction_score + time_score).label("final_score")
        return statement, final_score

    async def search_threads_with_count(
        self,
        query: ThreadSearchQuery,
        *,
        limit: int,
        total_display_count: int,
        exploration_factor: float,
        strength_weight: float,
        time_decay: float = SearchConfigDefaults.REDDIT_HOT_TIME_DECAY.value,
        offset: int = 0,
        exclude_thread_ids: Sequence[int | str] | None = None,
        redis_client=None,
        debug_timing: bool = False,
    ) -> tuple[Sequence[Thread], int]:
        """
        根据搜索条件搜索帖子并分页
        """
        try:
            # ── 调试计时 ──
            if debug_timing:
                t0 = time.perf_counter()

            # 清洗查询数据
            CleanedQo = self._clean_query(query, exclude_thread_ids)

            if debug_timing:
                t_clean = time.perf_counter()

            # --- 步骤 1: 构建过滤器列表 ---
            filters = []

            # 只搜索 not_found_count == 0 的帖子，避免显示被软删除的帖子
            filters.append(Thread.not_found_count == 0)

            # 只搜索 show_flag == True 的帖子，避免显示被隐藏的帖子
            filters.append(Thread.show_flag)

            # 当指定了 guild_id 且没有指定具体 channel_ids 时，按服务器过滤
            if query.guild_id and not query.channel_ids:
                filters.append(Thread.guild_id == query.guild_id)
            if query.channel_ids:
                filters.append(Thread.channel_id.in_(query.channel_ids))  # type: ignore

            # 处理屏蔽的频道 ID
            if query.exclude_channel_ids:
                filters.append(~Thread.channel_id.in_(query.exclude_channel_ids))  # type: ignore

            # 处理排除的帖子 ID
            if CleanedQo.normalized_exclude_thread_ids:
                filters.append(
                    ~Thread.thread_id.in_(CleanedQo.normalized_exclude_thread_ids)
                )  # type: ignore

            # 处理作者名搜索
            if CleanedQo.normalized_author_name:
                # 查找匹配的作者 ID，以便后续过滤
                search_pattern = f"%{CleanedQo.normalized_author_name}%"

                author_subquery = select(Author.id).where(
                    (
                        func.lower(Author.name)
                        == CleanedQo.normalized_author_name.lower()
                    )
                    | (Author.global_name.like(search_pattern))  # type: ignore
                    | (Author.display_name.like(search_pattern))  # type: ignore
                )  # type: ignore

                author_result = await self.session.execute(author_subquery)
                matched_author_ids = set(author_result.scalars().all())

                if query.include_authors:
                    # 如果同时指定了ID和名称，则取交集
                    CleanedQo.final_include_author_ids.intersection_update(
                        matched_author_ids
                    )
                else:
                    CleanedQo.final_include_author_ids = matched_author_ids

            # 应用作者过滤器
            if CleanedQo.final_include_author_ids:
                filters.append(
                    Thread.author_id.in_(list(CleanedQo.final_include_author_ids))  # type: ignore
                )
            if query.exclude_authors:
                filters.append(
                    Thread.author_id.notin_(query.exclude_authors)  # type: ignore
                )

            # 反应数范围过滤
            if query.reaction_count_range != (
                DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
            ):
                self._apply_range_filter(
                    filters, Thread.reaction_count, query.reaction_count_range
                )

            # 回复数范围过滤
            if query.reply_count_range != (
                DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
            ):
                self._apply_range_filter(
                    filters, Thread.reply_count, query.reply_count_range
                )

            # 创建时间范围过滤
            if CleanedQo.created_after_dt:
                filters.append(Thread.created_at >= CleanedQo.created_after_dt)
            if CleanedQo.created_before_dt:
                filters.append(Thread.created_at <= CleanedQo.created_before_dt)

            # 活跃时间范围过滤
            if CleanedQo.active_after_dt or CleanedQo.active_before_dt:
                # 对可能为 None 的 last_active_at 进行安全处理
                conditions = [Thread.last_active_at != None]  # noqa: E711
                if CleanedQo.active_after_dt:
                    conditions.append(
                        Thread.last_active_at >= CleanedQo.active_after_dt
                    )  # type: ignore
                if CleanedQo.active_before_dt:
                    conditions.append(
                        Thread.last_active_at <= CleanedQo.active_before_dt
                    )  # type: ignore
                filters.append(and_(*conditions))

            await require_current_tag_ids(
                self.session, [*query.include_tag_ids, *query.exclude_tag_ids]
            )
            # 标签过滤
            filters.extend(
                tag_filters(
                    "thread",
                    Thread.id,
                    query.include_tag_ids,
                    query.exclude_tag_ids,
                    query.tag_logic,
                )
            )
            filters.extend(
                await tag_name_filters(
                    self.session,
                    "thread",
                    Thread.id,
                    query.include_tags,
                    query.exclude_tags,
                    query.tag_logic,
                )
            )

            # 关键词匹配过滤
            thread_repo = ThreadRepository(self.session)

            # 处理 FTS 关键词搜索，返回子查询对象（不执行，留在 PG 内部）。
            fts_result = await thread_repo.get_fts_matched_thread_ids(
                keywords=query.keywords,
                exclude_keywords=query.exclude_keywords,
                exemption_markers=query.exclude_keyword_exemption_markers,
                redis_client=redis_client,
            )

            if fts_result.has_include:
                # 每个 AND 组是一个独立的 search_vector @@ tsquery 条件
                for cond in fts_result.include_conditions:
                    filters.append(cond)
            if fts_result.has_exclude:
                filters.append(~fts_result.exclude_condition)

            if debug_timing:
                t_fts = time.perf_counter()

            # 收藏搜索过滤器
            if query.user_id_for_collection_search:
                # 查询用户的帖子收藏记录，获取该用户收藏过的所有 thread_id
                collected_stmt = (
                    select(BooklistItem.thread_id)
                    .where(BooklistItem.owner_id == query.user_id_for_collection_search)
                    .distinct()
                )

                collected_result = await self.session.execute(collected_stmt)
                collected_thread_ids = list(collected_result.scalars().all())

                if not collected_thread_ids:
                    return [], 0

                # 添加过滤条件：帖子 thread_id 必须在该用户的收藏列表中
                filters.append(
                    Thread.thread_id.in_(collected_thread_ids)  # type: ignore
                )

            # --- 步骤 2: 组合所有过滤器 ---

            # 构建子查询：选择满足所有条件的 thread.id
            inner_stmt = select(Thread.id)
            if filters:
                inner_stmt = inner_stmt.where(and_(*filters))

            # --- 步骤 3: 使用 CTE 物化一次，COUNT 和数据查询复用 ---

            inner_cte = inner_stmt.cte("matched_ids")

            # 在 PG 内部统计满足条件的帖子总数（复用 CTE）
            count_stmt = select(func.count()).select_from(inner_cte)
            total_count = (await self.session.execute(count_stmt)).scalar_one()

            if debug_timing:
                t_cte = time.perf_counter()

            if total_count == 0:
                if debug_timing:
                    logger.info(
                        f"[计时] DB内部 | clean={(t_clean - t0) * 1000:.0f}ms "
                        f"fts={(t_fts - t_clean) * 1000:.0f}ms "
                        f"cte+count={(t_cte - t_fts) * 1000:.0f}ms "
                        f"select=0ms | matched=0"
                    )
                return [], 0

            # --- 步骤 4: 用 CTE 获取完整数据并分页 ---
            final_select_stmt = (
                select(Thread)
                .where(Thread.id.in_(select(inner_cte.c.id)))  # type: ignore
                .options(
                    selectinload(Thread.tags),  # type: ignore
                    joinedload(Thread.author),  # type: ignore
                )
            )

            order_by = None

            # 如果是自定义搜索，则使用其基础排序算法，否则使用主排序算法
            effective_sort_method = (
                query.custom_base_sort
                if query.sort_method == "custom"
                else query.sort_method
            )

            # 如果按收藏时间排序，但不是收藏搜索，则退回综合排序
            if (
                effective_sort_method == "collected_at"
                and not query.user_id_for_collection_search
            ):
                effective_sort_method = "comprehensive"

            if effective_sort_method == "comprehensive":
                # 按综合排序
                final_select_stmt, final_score_expr = self._apply_ucb1_ranking(
                    final_select_stmt,
                    total_display_count,
                    exploration_factor,
                    strength_weight,
                )
                order_by = (
                    final_score_expr.desc()
                    if query.sort_order == "desc"
                    else final_score_expr.asc()
                )
            elif effective_sort_method == "reddit_hot":
                # 按 Reddit Hot 热门排序
                final_select_stmt, final_score_expr = self._apply_reddit_hot_ranking(
                    final_select_stmt, time_decay
                )
                order_by = (
                    final_score_expr.desc()
                    if query.sort_order == "desc"
                    else final_score_expr.asc()
                )
            elif (
                effective_sort_method == "collected_at"
                and query.user_id_for_collection_search
            ):
                # 按收藏时间排序
                final_select_stmt = final_select_stmt.join(
                    BooklistItem,
                    and_(
                        Thread.thread_id == BooklistItem.thread_id,
                        BooklistItem.owner_id == query.user_id_for_collection_search,
                    ),
                ).group_by(Thread.id)  # type: ignore

                # 取最新的收藏时间
                sort_col = func.max(BooklistItem.created_at)
                order_by = (
                    sort_col.desc() if query.sort_order == "desc" else sort_col.asc()
                )
            else:
                # 按对应统计数据排序
                sort_col_name = (
                    effective_sort_method
                    if hasattr(Thread, effective_sort_method)
                    else "last_active_at"
                )
                sort_col = getattr(Thread, sort_col_name)
                order_by = (
                    sort_col.desc() if query.sort_order == "desc" else sort_col.asc()
                )

            # 应用排序
            if order_by is not None:
                final_select_stmt = final_select_stmt.order_by(order_by)

            # 应用偏移和返回数
            if offset:
                final_select_stmt = final_select_stmt.offset(offset)
            final_select_stmt = final_select_stmt.limit(limit)

            result = await self.session.execute(final_select_stmt)
            threads = result.scalars().all()

            if debug_timing:
                t_select = time.perf_counter()
                logger.info(
                    f"[计时] DB内部 | clean={(t_clean - t0) * 1000:.0f}ms "
                    f"fts={(t_fts - t_clean) * 1000:.0f}ms "
                    f"cte+count={(t_cte - t_fts) * 1000:.0f}ms "
                    f"select={(t_select - t_cte) * 1000:.0f}ms "
                    f"| matched={total_count}"
                )

            return threads, total_count

        except Exception:
            logging.error(
                "Error during search_threads_with_count execution", exc_info=True
            )
            raise

    async def get_tags_for_author(
        self, author_id: int, *, include_abyss: bool = True
    ) -> Sequence[Tag]:
        """获取指定作者发布过的所有帖子的唯一标签列表"""
        statement = (
            select(Tag)
            .join(Thread, Tag.threads)  # type: ignore
            .where(Thread.author_id == author_id)  # type: ignore
            .distinct()
        )
        if not include_abyss:
            statement = statement.where(Tag.is_abyss.is_(False))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_thread_by_discord_id(
        self,
        discord_thread_id: int,
        exclude_channel_ids: list[int] | None = None,
    ) -> Thread | None:
        """按 Discord thread_id 取单帖（含标签与作者），仅返回仍参与搜索的帖子。"""
        statement = (
            select(Thread)
            .where(
                Thread.thread_id == discord_thread_id,  # type: ignore[arg-type]
                Thread.not_found_count == 0,
                Thread.show_flag,
            )
            .options(
                selectinload(Thread.tags),  # type: ignore
                joinedload(Thread.author),  # type: ignore
            )
        )
        if exclude_channel_ids:
            statement = statement.where(
                Thread.channel_id.notin_(exclude_channel_ids)  # type: ignore[arg-type]
            )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_tags_for_collections(
        self, user_id: int, *, include_abyss: bool = True
    ) -> Sequence[Tag]:
        """获取指定用户收藏的所有帖子的唯一标签列表"""

        statement = (
            select(Tag)
            .join(TagBinding, Tag.id == TagBinding.tag_id)  # type: ignore
            .join(Thread, TagBinding.target_id == Thread.id)  # type: ignore
            .join(
                BooklistItem,
                Thread.thread_id == BooklistItem.thread_id,  # type: ignore
            )
            .where(
                BooklistItem.owner_id == user_id,
                TagBinding.target_type == "thread",
                TagBinding.ended_at.is_(None),
                Tag.deleted_at.is_(None),
            )
            .distinct()
        )
        if not include_abyss:
            statement = statement.where(Tag.is_abyss.is_(False))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_tag_usage_counts(self, tag_ids: list[int]) -> dict[int, int]:
        """批量查询每个 tag_id 关联的帖子数量，用于评估标签流行度。

        缺失的 tag_id 不在返回字典中（调用方自行视为 0）。
        """
        if not tag_ids:
            return {}

        stmt = (
            select(TagBinding.tag_id, func.count(TagBinding.target_id))
            .join(Tag, Tag.id == TagBinding.tag_id)
            .where(
                TagBinding.tag_id.in_(tag_ids),
                TagBinding.target_type == "thread",
                TagBinding.ended_at.is_(None),
                Tag.deleted_at.is_(None),
            )  # type: ignore[arg-type]
            .group_by(TagBinding.tag_id)
        )
        result = await self.session.execute(stmt)
        return {tag_id: count for tag_id, count in result.all()}

    async def find_similar_threads(
        self,
        source_thread: Thread,
        *,
        limit: int = 5,
        exclude_channel_ids: list[int] | None = None,
        ucb1_config: SearchConfigDTO,
    ) -> tuple[list[Thread], int]:
        """基于 TAG 匹配度的相似帖子推荐。

        降级策略：
          1. 按 source_thread.tags 流行度（关联帖子数）降序，得到 ordered_tags。
          2. k 从 len(ordered_tags) 递减到 1：
             - 取流行度最高的前 k 个 tag（即丢弃末尾流行度最低的 n-k 个）；
             - 用 tag_logic='and' 调用 search_threads_with_count；
             - 跨级累计去重（exclude_thread_ids）；
             - 排序用 reddit_hot。
          3. 命中累计等于 limit 时立即返回；若所有级别跑完仍不足，返回已有结果。

        Returns:
            (threads, matched_tag_count)
            matched_tag_count 为最后一次命中贡献结果时使用的 TAG 个数；
            若没有任何命中则为 0。
        """
        if limit <= 0 or source_thread is None:
            return [], 0

        source_tags: list[Tag] = list(getattr(source_thread, "tags", []) or [])
        if not source_tags:
            return [], 0

        # 按 tag_id 查流行度，再按流行度降序排列 tag_name
        tag_id_to_name: dict[int, str] = {
            t.id: t.name for t in source_tags if t.id is not None
        }
        usage_counts = await self.get_tag_usage_counts(list(tag_id_to_name.keys()))

        # 同名 tag 可能有多个 ID，合并使用数；并去重 name
        name_to_count: dict[str, int] = {}
        for tid, name in tag_id_to_name.items():
            name_to_count[name] = name_to_count.get(name, 0) + usage_counts.get(tid, 0)

        if not name_to_count:
            return [], 0

        # 流行度降序；同流行度时按 name 稳定排序以保证幂等性
        ordered_tag_names: list[str] = sorted(
            name_to_count.keys(), key=lambda n: (-name_to_count[n], n)
        )

        source_discord_id = source_thread.thread_id
        collected: list[Thread] = []
        seen_discord_ids: set[int] = {source_discord_id}
        matched_tag_count = 0

        # k 从全量降到 1，每次取流行度最高的 k 个 tag
        for k in range(len(ordered_tag_names), 0, -1):
            current_tags = ordered_tag_names[:k]
            query = ThreadSearchQuery(
                guild_id=None,
                channel_ids=None,
                exclude_channel_ids=list(exclude_channel_ids or []) or None,
                include_tags=current_tags,
                exclude_tags=[],
                tag_logic="and",
                sort_method="reddit_hot",
                sort_order="desc",
            )

            remaining = limit - len(collected)
            if remaining <= 0:
                break

            threads, _total = await self.search_threads_with_count(
                query,
                limit=remaining,
                total_display_count=ucb1_config.total_display_count,
                exploration_factor=ucb1_config.exploration_factor,
                strength_weight=ucb1_config.strength_weight,
                time_decay=ucb1_config.reddit_hot_time_decay,
                exclude_thread_ids=list(seen_discord_ids),
            )

            new_threads = [t for t in threads if t.thread_id not in seen_discord_ids]
            if new_threads:
                matched_tag_count = k
                for t in new_threads:
                    collected.append(t)
                    seen_discord_ids.add(t.thread_id)
                    if len(collected) >= limit:
                        break

            if len(collected) >= limit:
                break

        return collected, matched_tag_count

    async def build_similar_thread_candidates(
        self,
        source_thread_id: int,
        *,
        candidate_limit: int,
        exclude_channel_ids: list[int] | None,
        ucb1_config: SearchConfigDTO,
        timeout_seconds: float,
    ) -> tuple[list[SimilarThreadCandidateDTO], bool]:
        """按现有逐级放宽逻辑构建只包含 ID 的共享候选池。"""
        if candidate_limit <= 0:
            return [], True

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds

        # 冷构建仅投影源帖 ID 与标签，避免加载完整 ORM 实体和作者。
        source = await asyncio.wait_for(
            self._get_similar_thread_source(
                source_thread_id,
                exclude_channel_ids=exclude_channel_ids,
            ),
            timeout=max(0.001, deadline - loop.time()),
        )
        if source is None:
            raise LookupError("源帖不存在或当前用户不可查看")
        if not source.tags:
            return [], True

        tag_id_to_name = {tag.tag_id: tag.tag_name for tag in source.tags}
        usage_counts = await asyncio.wait_for(
            self.get_tag_usage_counts(list(tag_id_to_name.keys())),
            timeout=max(0.001, deadline - loop.time()),
        )

        name_to_count: dict[str, int] = {}
        for tag_id, tag_name in tag_id_to_name.items():
            name_to_count[tag_name] = name_to_count.get(tag_name, 0) + usage_counts.get(
                tag_id, 0
            )
        ordered_tag_names = sorted(
            name_to_count, key=lambda name: (-name_to_count[name], name)
        )

        candidates: list[SimilarThreadCandidateDTO] = []
        seen_thread_ids = {source.thread_id}
        for matched_tag_count in range(len(ordered_tag_names), 0, -1):
            remaining = candidate_limit - len(candidates)
            if remaining <= 0:
                return candidates, True
            try:
                thread_ids = await asyncio.wait_for(
                    self._find_similar_candidate_ids(
                        tag_names=ordered_tag_names[:matched_tag_count],
                        limit=remaining,
                        exclude_thread_ids=seen_thread_ids,
                        exclude_channel_ids=exclude_channel_ids,
                        time_decay=ucb1_config.reddit_hot_time_decay,
                    ),
                    timeout=max(0.001, deadline - loop.time()),
                )
            except asyncio.TimeoutError:
                if candidates:
                    return candidates, False
                raise

            for thread_id in thread_ids:
                if thread_id in seen_thread_ids:
                    continue
                candidates.append(
                    SimilarThreadCandidateDTO(
                        thread_id=thread_id,
                        matched_tag_count=matched_tag_count,
                    )
                )
                seen_thread_ids.add(thread_id)

        return candidates, True

    async def _get_similar_thread_source(
        self,
        source_thread_id: int,
        *,
        exclude_channel_ids: list[int] | None,
    ) -> SimilarThreadSourceDTO | None:
        """用单条投影查询读取可访问源帖及其标签。"""
        filters = [
            Thread.thread_id == source_thread_id,
            Thread.not_found_count == 0,
            Thread.show_flag,
        ]
        if exclude_channel_ids:
            filters.append(
                Thread.channel_id.notin_(exclude_channel_ids)  # type: ignore[arg-type]
            )

        # 外连接确保无标签的合法源帖仍能与无权限、已删除源帖区分。
        statement = (
            select(Thread.thread_id, Tag.id, Tag.name)
            .select_from(Thread)
            .outerjoin(
                TagBinding,
                and_(
                    Thread.id == TagBinding.target_id,
                    TagBinding.target_type == "thread",
                    TagBinding.ended_at.is_(None),
                ),  # type: ignore[arg-type]
            )
            .outerjoin(Tag, and_(TagBinding.tag_id == Tag.id, Tag.deleted_at.is_(None)))  # type: ignore[arg-type]
            .where(*filters)
        )
        rows = (await self.session.execute(statement)).all()
        if not rows:
            return None

        tags = [
            SimilarThreadSourceTagDTO(tag_id=tag_id, tag_name=tag_name)
            for _, tag_id, tag_name in rows
            if tag_id is not None and tag_name is not None
        ]
        return SimilarThreadSourceDTO(thread_id=rows[0][0], tags=tags)

    async def filter_and_rank_similar_candidates(
        self,
        candidates: list[SimilarThreadCandidateDTO],
        *,
        limit: int,
        prefs: UserSearchPreferencesDTO | None,
        exclude_channel_ids: list[int] | None,
        time_decay: float,
        redis_client=None,
    ) -> tuple[list[Thread], int]:
        """实时应用用户反选项，并按匹配层级和最新 Reddit Hot 排序。"""
        if not candidates or limit <= 0:
            return [], 0

        candidate_ids = [candidate.thread_id for candidate in candidates]
        matched_levels = {
            candidate.thread_id: candidate.matched_tag_count for candidate in candidates
        }
        original_positions = {
            candidate.thread_id: index for index, candidate in enumerate(candidates)
        }
        filters = [
            Thread.thread_id.in_(candidate_ids),  # type: ignore[arg-type]
            Thread.not_found_count == 0,
            Thread.show_flag,
        ]
        if exclude_channel_ids:
            filters.append(
                Thread.channel_id.notin_(exclude_channel_ids)  # type: ignore[arg-type]
            )
        filters.extend(
            await self._build_preference_exclusion_filters(prefs, redis_client)
        )

        statement = select(Thread).where(and_(*filters))
        statement = statement.options(
            selectinload(Thread.tags),  # type: ignore
            joinedload(Thread.author),  # type: ignore
        )
        statement, hot_score = self._apply_reddit_hot_ranking(statement, time_decay)
        matched_level = case(
            matched_levels,
            value=Thread.thread_id,
            else_=0,
        )
        original_position = case(
            original_positions,
            value=Thread.thread_id,
            else_=len(candidates),
        )
        statement = statement.order_by(
            matched_level.desc(), hot_score.desc(), original_position.asc()
        ).limit(limit)

        result = await self.session.execute(statement)
        threads = list(result.scalars().unique().all())
        selected_levels = [matched_levels[thread.thread_id] for thread in threads]
        return threads, min(selected_levels, default=0)

    async def get_preference_filtered_thread_guilds(
        self,
        thread_ids: list[int],
        *,
        prefs: UserSearchPreferencesDTO | None,
        channel_mappings_config: dict[int, list[dict]] | None = None,
        redis_client=None,
    ) -> dict[int, int]:
        """批量返回符合可见性和用户反选偏好的帖子及服务器 ID。"""
        if not thread_ids:
            return {}

        # 将虚拟反选标签解析为频道范围，只保留真实标签进入标签过滤。
        effective_prefs = prefs
        channel_ids = None
        if prefs and prefs.exclude_tags:
            thread_repo = ThreadRepository(self.session)
            all_channel_ids = list(await thread_repo.get_all_indexed_channel_ids())
            channel_result = ChannelMappingUtils(channel_mappings_config or {}).resolve(
                channel_ids=None,
                include_tags=[],
                exclude_tags=prefs.exclude_tags,
                tag_logic="or",
                all_indexed_channels=all_channel_ids,
            )
            if channel_result.effective_channel_ids == []:
                return {}
            channel_ids = channel_result.effective_channel_ids
            effective_prefs = prefs.model_copy(
                update={"exclude_tags": channel_result.effective_exclude_tags}
            )

        # 限定候选帖子及其可见性。
        filters = [
            Thread.thread_id.in_(thread_ids),  # type: ignore[arg-type]
            Thread.not_found_count == 0,
            Thread.show_flag,
        ]
        if channel_ids is not None:
            filters.append(
                Thread.channel_id.in_(channel_ids)  # type: ignore[arg-type]
            )

        # 复用搜索使用的作者、真实标签和全文关键词反选规则。
        filters.extend(
            await self._build_preference_exclusion_filters(
                effective_prefs, redis_client
            )
        )
        statement = select(Thread.thread_id, Thread.guild_id).where(and_(*filters))
        rows = (await self.session.execute(statement)).all()
        return {thread_id: guild_id for thread_id, guild_id in rows}

    async def _build_preference_exclusion_filters(
        self,
        prefs: UserSearchPreferencesDTO | None,
        redis_client=None,
    ) -> list:
        """构建搜索场景共用的用户反选过滤条件。"""
        if prefs is None:
            return []

        filters = []
        if prefs.exclude_authors:
            filters.append(
                Thread.author_id.notin_(prefs.exclude_authors)  # type: ignore[arg-type]
            )

        if prefs.exclude_tags:
            excluded_tag_ids = [
                tag_id
                for tag_name in prefs.exclude_tags
                for tag_id in self.tag_cache_service.get_ids_by_tag_name(tag_name)
            ]
            if excluded_tag_ids:
                filters.append(~Thread.tags.any(Tag.id.in_(excluded_tag_ids)))  # type: ignore

        if prefs.exclude_keywords:
            thread_repo = ThreadRepository(self.session)
            fts_result = await thread_repo.get_fts_matched_thread_ids(
                keywords=None,
                exclude_keywords=prefs.exclude_keywords,
                exemption_markers=prefs.exclude_keyword_exemption_markers,
                redis_client=redis_client,
            )
            if fts_result.has_exclude:
                filters.append(~fts_result.exclude_condition)

        return filters

    async def _find_similar_candidate_ids(
        self,
        *,
        tag_names: list[str],
        limit: int,
        exclude_thread_ids: set[int],
        exclude_channel_ids: list[int] | None,
        time_decay: float,
    ) -> list[int]:
        """查询一个标签匹配层级的候选 Discord 帖子 ID。"""
        filters = [Thread.not_found_count == 0, Thread.show_flag]
        if exclude_thread_ids:
            filters.append(
                Thread.thread_id.notin_(exclude_thread_ids)  # type: ignore[arg-type]
            )
        if exclude_channel_ids:
            filters.append(
                Thread.channel_id.notin_(exclude_channel_ids)  # type: ignore[arg-type]
            )
        for tag_name in tag_names:
            tag_ids = self.tag_cache_service.get_ids_by_tag_name(tag_name)
            if not tag_ids:
                return []
            filters.append(Thread.tags.any(Tag.id.in_(tag_ids)))  # type: ignore

        statement = select(Thread.thread_id).where(and_(*filters))
        statement, hot_score = self._apply_reddit_hot_ranking(statement, time_decay)
        statement = statement.order_by(hot_score.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
