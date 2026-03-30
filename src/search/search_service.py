import asyncio
import logging
import re
from functools import partial
from typing import Sequence

import rjieba
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Float, and_, case, cast, func, select

from core.tag_cache_service import TagCacheService
from models import Author, Tag, Thread, ThreadTagLink, UserCollection
from search.qo.thread_search import ThreadSearchQuery
from shared.database import thread_fts_table
from shared.enum.collection_type import CollectionType
from shared.enum.default_preferences import DefaultPreferences
from shared.range_parser import parse_range_string
from shared.time_parser import parse_time_string


class SearchService:
    """封装与搜索相关的数据库操作。"""

    def __init__(self, session: AsyncSession, tag_cache_service: TagCacheService):
        self.session = session
        self.tag_cache_service = tag_cache_service

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

    async def search_threads_with_count(
        self,
        query: ThreadSearchQuery,
        *,
        limit: int,
        total_display_count: int,
        exploration_factor: float,
        strength_weight: float,
        offset: int = 0,
        exclude_thread_ids: Sequence[int | str] | None = None,
    ) -> tuple[Sequence[Thread], int]:
        """
        根据搜索条件搜索帖子并分页
        """
        try:
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

            # --- 步骤 0: 解析标签 ---
            resolved_include_tag_ids = [
                id
                for name in query.include_tags
                for id in self.tag_cache_service.get_ids_by_name(name)
            ]
            resolved_exclude_tag_ids = [
                id
                for name in query.exclude_tags
                for id in self.tag_cache_service.get_ids_by_name(name)
            ]

            # --- 步骤 1: 构建基础过滤器列表 (除了反选关键词) ---
            filters = []
            # 只搜索 not_found_count == 0 的帖子，避免显示被软删除的帖子
            filters.append(Thread.not_found_count == 0)
            # 当指定了 guild_id 且没有指定具体 channel_ids 时，按服务器过滤
            if query.guild_id and not query.channel_ids:
                filters.append(Thread.guild_id == query.guild_id)
            if query.channel_ids:
                filters.append(Thread.channel_id.in_(query.channel_ids))  # type: ignore
            if exclude_thread_ids:
                normalized_ids = []
                for tid in exclude_thread_ids:
                    try:
                        normalized_ids.append(int(tid))
                    except (TypeError, ValueError):
                        continue
                if normalized_ids:
                    filters.append(~Thread.thread_id.in_(normalized_ids))  # type: ignore

            final_include_author_ids = (
                set(query.include_authors) if query.include_authors else set()
            )

            if query.author_name:
                normalized_author_name = query.author_name.strip()
                if normalized_author_name:
                    # 使用子查询来查找匹配的作者 ID
                    search_pattern = f"%{normalized_author_name}%"
                    author_subquery = select(Author.id).where(
                        (func.lower(Author.name) == normalized_author_name.lower())
                        | (Author.global_name.like(search_pattern))  # type: ignore
                        | (Author.display_name.like(search_pattern))  # type: ignore
                    )  # type: ignore
                    author_result = await self.session.execute(author_subquery)
                    matched_author_ids = set(author_result.scalars().all())

                    if query.include_authors:
                        # 如果同时指定了ID和名称，则取交集
                        final_include_author_ids.intersection_update(matched_author_ids)
                    else:
                        final_include_author_ids = matched_author_ids

            # 应用作者过滤器
            if final_include_author_ids:
                filters.append(
                    Thread.author_id.in_(list(final_include_author_ids))  # type: ignore
                )
            if query.exclude_authors:
                filters.append(
                    Thread.author_id.notin_(query.exclude_authors)  # type: ignore
                )

            # --- 范围过滤---
            if query.reaction_count_range != (
                DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
            ):
                self._apply_range_filter(
                    filters, Thread.reaction_count, query.reaction_count_range
                )
            if query.reply_count_range != (
                DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
            ):
                self._apply_range_filter(
                    filters, Thread.reply_count, query.reply_count_range
                )

            if created_after_dt:
                filters.append(Thread.created_at >= created_after_dt)
            if created_before_dt:
                filters.append(Thread.created_at <= created_before_dt)

            # 对可能为 None (虽然不太可能，我说)的 last_active_at 进行安全处理
            if active_after_dt or active_before_dt:
                conditions = [Thread.last_active_at != None]  # noqa: E711
                if active_after_dt:
                    conditions.append(Thread.last_active_at >= active_after_dt)  # type: ignore
                if active_before_dt:
                    conditions.append(Thread.last_active_at <= active_before_dt)  # type: ignore
                filters.append(and_(*conditions))

            # -- 标签过滤 --
            if resolved_include_tag_ids:
                if query.tag_logic == "and":
                    # TODO : 考虑精简
                    for tag_name in query.include_tags:
                        ids_for_name = self.tag_cache_service.get_ids_by_name(tag_name)
                        if ids_for_name:
                            filters.append(Thread.tags.any(Tag.id.in_(ids_for_name)))  # type: ignore
                else:
                    filters.append(
                        Thread.tags.any(Tag.id.in_(resolved_include_tag_ids))  # type: ignore
                    )  # type: ignore
            if resolved_exclude_tag_ids:
                filters.append(
                    ~Thread.tags.any(Tag.id.in_(resolved_exclude_tag_ids))  # type: ignore
                )

            # --- 步骤 2: 独立执行 FTS 查询，拿到匹配/排除的 ID 集合 ---
            loop = asyncio.get_running_loop()

            # 2a. 反选关键词 → 获取要排除的 thread ID
            fts_exclude_ids: set[int] = set()
            if query.exclude_keywords:
                exemption_markers = (
                    query.exclude_keyword_exemption_markers
                    if query.exclude_keyword_exemption_markers is not None
                    else ["禁", "🈲"]
                )
                exclude_keywords_list = [
                    kw.strip()
                    for kw in re.split(r"[,，/\s]+", query.exclude_keywords)
                    if kw.strip()
                ]

                all_exclude_parts = []
                for keyword in exclude_keywords_list:
                    raw_tokens = await loop.run_in_executor(
                        None, partial(rjieba.cut, keyword)
                    )
                    tokens = [tok.strip() for tok in raw_tokens if tok.strip()]
                    if not tokens:
                        continue

                    match_parts = [f'"{tok}"' for tok in tokens[:-1]]
                    match_parts.append(f'"{tokens[-1]}"*')
                    match_expr = " AND ".join(match_parts)

                    if exemption_markers:
                        first_token = tokens[0]
                        exemption_clauses = [
                            f'NEAR("{first_token}" "{marker}", 4)'
                            for marker in exemption_markers
                        ]
                        exemption_match_str = f"({' OR '.join(exemption_clauses)})"
                        all_exclude_parts.append(
                            f"({match_expr}) NOT {exemption_match_str}"
                        )
                    else:
                        all_exclude_parts.append(f"({match_expr})")

                if all_exclude_parts:
                    final_exclude_expr = " OR ".join(all_exclude_parts)
                    exc_result = await self.session.execute(
                        select(thread_fts_table.c.rowid).where(
                            thread_fts_table.c.thread_fts.op("MATCH")(
                                final_exclude_expr
                            )
                        )
                    )
                    fts_exclude_ids = set(exc_result.scalars().all())

            # 2b. 正选关键词 → 获取匹配的 thread ID（多组取交集）
            fts_include_ids: set[int] | None = None
            if query.keywords:
                keywords_str = query.keywords.replace("，", ",").replace("／", "/")
                and_groups = [
                    group.strip()
                    for group in keywords_str.split(",")
                    if group.strip()
                ]
                for group in and_groups:
                    or_keywords = []
                    for kw in group.split("/"):
                        kw = kw.strip()
                        if not kw:
                            continue
                        if kw.startswith('"') and kw.endswith('"') and len(kw) > 2:
                            exact_kw = kw[1:-1].strip()
                            if exact_kw:
                                or_keywords.append(f'"{exact_kw}"')
                        else:
                            raw_tokens = await loop.run_in_executor(
                                None, partial(rjieba.cut, kw)
                            )
                            tokens = [t.strip() for t in raw_tokens if t.strip()]
                            if tokens:
                                expr = " ".join(f"{t}*" for t in tokens)
                                or_keywords.append(
                                    f"({expr})" if len(tokens) > 1 else expr
                                )

                    if or_keywords:
                        match_str = " OR ".join(or_keywords)
                        grp_result = await self.session.execute(
                            select(thread_fts_table.c.rowid).where(
                                thread_fts_table.c.thread_fts.op("MATCH")(match_str)
                            )
                        )
                        group_ids = set(grp_result.scalars().all())
                        if fts_include_ids is None:
                            fts_include_ids = group_ids
                        else:
                            fts_include_ids &= group_ids

                if fts_include_ids is not None and not fts_include_ids:
                    return [], 0

            # 2c. 合并 FTS 结果到过滤器（纯 ID 集合，不再 JOIN thread_fts）
            if fts_include_ids is not None:
                final_fts_ids = fts_include_ids - fts_exclude_ids
                if not final_fts_ids:
                    return [], 0
                filters.append(Thread.id.in_(final_fts_ids))  # type: ignore
            elif fts_exclude_ids:
                filters.append(Thread.id.not_in(fts_exclude_ids))  # type: ignore

            # --- 步骤 3: 组合其他过滤器（不再 JOIN thread_fts）---
            base_stmt = select(Thread.id).distinct()

            if query.user_id_for_collection_search:
                from shared.enum.collection_type import CollectionType

                base_stmt = base_stmt.join(
                    UserCollection,
                    and_(
                        Thread.thread_id == UserCollection.target_id,
                        UserCollection.target_type == CollectionType.THREAD,
                    ),  # type: ignore
                )
                filters.append(
                    UserCollection.user_id == query.user_id_for_collection_search
                )

            # 应用所有过滤器
            if filters:
                base_stmt = base_stmt.where(and_(*filters))

            # --- 步骤 4: 一次性执行 ID 查询（FTS MATCH 只跑一次）---
            id_result = await self.session.execute(base_stmt)
            matched_ids = list(id_result.scalars().all())
            total_count = len(matched_ids)

            if total_count == 0:
                return [], 0

            # --- 步骤 5: 用具体 ID 列表获取分页数据（无嵌套子查询）---
            final_select_stmt = (
                select(Thread)
                .where(Thread.id.in_(matched_ids))  # type: ignore
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
            elif (
                effective_sort_method == "collected_at"
                and query.user_id_for_collection_search
            ):
                # 按收藏时间排序
                final_select_stmt = final_select_stmt.join(
                    UserCollection,
                    and_(
                        Thread.thread_id == UserCollection.target_id,
                        UserCollection.target_type == CollectionType.THREAD,
                        UserCollection.user_id == query.user_id_for_collection_search,
                    ),
                )
                sort_col = getattr(UserCollection, "created_at")
                order_by = (
                    sort_col.desc() if query.sort_order == "desc" else sort_col.asc()
                )
            else:
                sort_col_name = (
                    effective_sort_method
                    if hasattr(Thread, effective_sort_method)
                    else "last_active_at"
                )
                sort_col = getattr(Thread, sort_col_name)
                order_by = (
                    sort_col.desc() if query.sort_order == "desc" else sort_col.asc()
                )

            if order_by is not None:
                final_select_stmt = final_select_stmt.order_by(order_by)

            if offset:
                final_select_stmt = final_select_stmt.offset(offset)
            final_select_stmt = final_select_stmt.limit(limit)

            result = await self.session.execute(final_select_stmt)
            threads = result.scalars().all()

            return threads, total_count

        except Exception:
            logging.error(
                "Error during search_threads_with_count execution", exc_info=True
            )
            raise

    async def get_tags_for_author(self, author_id: int) -> Sequence[Tag]:
        """获取指定作者发布过的所有帖子的唯一标签列表"""
        statement = (
            select(Tag)
            .join(Thread, Tag.threads)  # type: ignore
            .where(Thread.author_id == author_id)  # type: ignore
            .distinct()
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_tags_for_collections(self, user_id: int) -> Sequence[Tag]:
        """获取指定用户收藏的所有帖子的唯一标签列表"""

        statement = (
            select(Tag)
            .join(ThreadTagLink, Tag.id == ThreadTagLink.tag_id)  # type: ignore
            .join(Thread, ThreadTagLink.thread_id == Thread.id)  # type: ignore
            .join(
                UserCollection,
                and_(
                    Thread.thread_id == UserCollection.target_id,
                    UserCollection.target_type == CollectionType.THREAD,
                ),  # type: ignore
            )
            .where(UserCollection.user_id == user_id)
            .distinct()
        )
        result = await self.session.execute(statement)
        return result.scalars().all()
