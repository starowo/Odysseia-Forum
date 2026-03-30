from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.v1.dependencies.security import get_current_user, require_auth
from api.v1.schemas.banner import BannerItem
from api.v1.schemas.search import SearchRequest, SearchResponse, ThreadDetail
from api.v1.schemas.search.author import AuthorDetail
from banner.banner_service import BannerService
from collection.cog import CollectionCog
from core.collection_service import CollectionService
from config.config_service import ConfigService
from core.cache_service import CacheService
from search.cog import Search
from search.qo.thread_search import ThreadSearchQuery
from search.search_service import SearchService
from shared.enum.collection_type import CollectionType
from shared.enum.search_config_type import SearchConfigDefaults, SearchConfigType
from shared.keyword_parser import KeywordParser
from ThreadManager.services.follow_service import FollowService

# 全局变量，将在应用启动时由 bot_main.py 注入
search_cog_instance: Search | None = None
collection_cog_instance: CollectionCog | None = None
async_session_factory: async_sessionmaker | None = None
config_service_instance: ConfigService | None = None
cache_service_instance: CacheService | None = None
# 频道映射配置: { target_channel_id: [ { "tag_name": str, "source_channel_ids": [int] } ] }
channel_mappings_config: Dict[int, List[Dict]] = {}

router = APIRouter(
    prefix="/search", tags=["帖子搜索"], dependencies=[Depends(require_auth)]
)


@router.post("/", response_model=SearchResponse, summary="执行帖子搜索")
async def execute_search(
    request: SearchRequest, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    根据指定的条件搜索帖子，并返回包含作者信息的分页结果。

    - request: 搜索请求参数，包含所有搜索条件
    - return: 分页的搜索结果，包含帖子列表和总数
    """
    if (
        not search_cog_instance
        or not collection_cog_instance
        or not async_session_factory
        or not config_service_instance
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search 服务尚未初始化",
        )

    # 解析高级搜索语法
    author_name = None
    parsed_include_keywords = []
    parsed_exclude_keywords = []
    remaining_keywords = request.keywords or ""

    if request.keywords:
        # 清理并解析关键词
        sanitized_keywords = KeywordParser.sanitize(request.keywords)
        (
            author_name,
            parsed_include_keywords,
            parsed_exclude_keywords,
            remaining_keywords,
        ) = KeywordParser.parse(sanitized_keywords)

    # 合并解析出的排除词和原有的排除词
    final_exclude_keywords = request.exclude_keywords or ""
    if parsed_exclude_keywords:
        if final_exclude_keywords:
            final_exclude_keywords += " " + " ".join(parsed_exclude_keywords)
        else:
            final_exclude_keywords = " ".join(parsed_exclude_keywords)

    # 构建最终的关键词字符串（精确匹配的用引号包围）
    final_keywords_parts = []
    if parsed_include_keywords:
        # 精确匹配的关键词用引号包围
        for kw in parsed_include_keywords:
            final_keywords_parts.append(f'"{kw}"')
    if remaining_keywords:
        final_keywords_parts.append(remaining_keywords)

    final_keywords = " ".join(final_keywords_parts) if final_keywords_parts else None

    # 处理收藏搜索
    user_id_for_collection_search = None
    if request.search_by_collection and current_user and "id" in current_user:
        user_id_for_collection_search = int(current_user["id"])

    # 处理频道映射虚拟标签
    effective_channel_ids = list(request.channel_ids) if request.channel_ids else None
    effective_include_tags = list(request.include_tags)
    effective_exclude_tags = list(request.exclude_tags)
    # 记录实际搜索的频道集合，用于之后构建 available_tags
    searched_channel_ids: set[int] = set()

    has_mapping = False
    if effective_channel_ids and len(effective_channel_ids) == 1:
        origin_channel_id = effective_channel_ids[0]
        mappings = channel_mappings_config.get(origin_channel_id, [])
        if mappings:
            has_mapping = True
            virtual_tag_set = {m["tag_name"] for m in mappings}
            mapping_tag_lookup = {m["tag_name"]: m for m in mappings}

            # 分离虚拟标签和真实标签
            included_virtual = [
                t for t in effective_include_tags if t in virtual_tag_set
            ]
            excluded_virtual = [
                t for t in effective_exclude_tags if t in virtual_tag_set
            ]
            effective_include_tags = [
                t for t in effective_include_tags if t not in virtual_tag_set
            ]
            effective_exclude_tags = [
                t for t in effective_exclude_tags if t not in virtual_tag_set
            ]

            excluded_channels: set[int] = set()
            for vt in excluded_virtual:
                excluded_channels.update(
                    mapping_tag_lookup[vt].get("source_channel_ids", [])
                )

            if included_virtual:
                # 有选中的虚拟标签 → 只搜索选中标签对应频道的交集
                channel_sets = []
                for vt in included_virtual:
                    channel_sets.append(
                        set(mapping_tag_lookup[vt].get("source_channel_ids", []))
                    )
                intersected = channel_sets[0]
                for cs in channel_sets[1:]:
                    intersected &= cs
                intersected -= excluded_channels
                effective_channel_ids = list(intersected)
            else:
                # 无选中虚拟标签 → 搜索原频道 + 所有映射频道（排除被排除的）
                all_mapped: set[int] = set()
                for m in mappings:
                    all_mapped.update(m.get("source_channel_ids", []))
                all_mapped -= excluded_channels
                effective_channel_ids = [origin_channel_id] + list(all_mapped)

            searched_channel_ids = set(effective_channel_ids)

    query_object = ThreadSearchQuery(
        guild_id=request.guild_id,
        channel_ids=effective_channel_ids,
        include_tags=effective_include_tags,
        exclude_tags=effective_exclude_tags,
        tag_logic=request.tag_logic,
        keywords=final_keywords,
        exclude_keywords=final_exclude_keywords if final_exclude_keywords else None,
        exclude_keyword_exemption_markers=request.exclude_keyword_exemption_markers,
        include_authors=request.include_authors,
        exclude_authors=request.exclude_authors,
        author_name=author_name,
        created_after=request.created_after,
        created_before=request.created_before,
        active_after=request.active_after,
        active_before=request.active_before,
        reaction_count_range=request.reaction_count_range,
        reply_count_range=request.reply_count_range,
        sort_method=request.sort_method,
        sort_order=request.sort_order,
        custom_base_sort=request.custom_base_sort,
        user_id_for_collection_search=user_id_for_collection_search,
    )

    try:
        total_disp_conf = await config_service_instance.get_config_from_cache(
            SearchConfigType.TOTAL_DISPLAY_COUNT
        )
        ucb_factor_conf = await config_service_instance.get_config_from_cache(
            SearchConfigType.UCB1_EXPLORATION_FACTOR
        )
        strength_conf = await config_service_instance.get_config_from_cache(
            SearchConfigType.STRENGTH_WEIGHT
        )

        total_display_count = (
            total_disp_conf.value_int
            if total_disp_conf and total_disp_conf.value_int is not None
            else 1
        )
        exploration_factor = (
            ucb_factor_conf.value_float
            if ucb_factor_conf and ucb_factor_conf.value_float is not None
            else SearchConfigDefaults.UCB1_EXPLORATION_FACTOR.value
        )
        strength_weight = (
            strength_conf.value_float
            if strength_conf and strength_conf.value_float is not None
            else SearchConfigDefaults.STRENGTH_WEIGHT.value
        )

        exclude_thread_ids = request.exclude_thread_ids or []

        async with async_session_factory() as session:
            repo = SearchService(session, search_cog_instance.tag_service)
            threads, total_threads = await repo.search_threads_with_count(
                query_object,
                limit=request.limit,
                total_display_count=total_display_count,
                exploration_factor=exploration_factor,
                strength_weight=strength_weight,
                exclude_thread_ids=exclude_thread_ids,
            )

            # 当排序方法为按创建时间或收藏时间排序时，不记录展示次数
            count_view = not (
                query_object.sort_method in ["created_at", "collected_at"]
                or (
                    query_object.sort_method == "custom"
                    and query_object.custom_base_sort in ["created_at", "collected_at"]
                )
            )

            if threads and count_view:
                thread_ids_to_update = [t.id for t in threads if t.id is not None]
                await search_cog_instance.impression_cache_service.increment(
                    thread_ids_to_update
                )

            # 检查收藏状态（复用同一 session）
            collected_thread_ids = set()
            user_id = (
                int(current_user["id"]) if current_user and "id" in current_user else None
            )
            if user_id and threads:
                thread_ids = [t.thread_id for t in threads]
                collection_service = CollectionService(session)
                collected_thread_ids = await collection_service.get_collected_target_ids(
                    user_id, CollectionType.THREAD, thread_ids
                )

            # 预计算 channel_id → 匹配的虚拟标签名（用于帖子卡片标签展示）
            channel_to_virtual: dict[int, list[str]] = {}
            if has_mapping and effective_channel_ids:
                origin_ch = request.channel_ids[0] if request.channel_ids else None
                for m in channel_mappings_config.get(origin_ch or 0, []):
                    for src_id in m.get("source_channel_ids", []):
                        channel_to_virtual.setdefault(src_id, []).append(m["tag_name"])

            results = []
            for thread in threads:
                matched_virtual = channel_to_virtual.get(thread.channel_id, [])
                thread_detail = ThreadDetail(
                    thread_id=thread.thread_id,
                    guild_id=thread.guild_id,
                    channel_id=thread.channel_id,
                    title=thread.title,
                    author=AuthorDetail.model_validate(thread.author)
                    if thread.author
                    else None,
                    created_at=thread.created_at,
                    last_active_at=thread.last_active_at,
                    reaction_count=thread.reaction_count,
                    reply_count=thread.reply_count,
                    display_count=thread.display_count,
                    first_message_excerpt=thread.first_message_excerpt,
                    thumbnail_urls=thread.thumbnail_urls or [],
                    tags=[tag.name for tag in thread.tags],
                    virtual_tags=matched_virtual,
                    collected_flag=thread.thread_id in collected_thread_ids,
                )
                results.append(thread_detail)

            # 构建 available_tags：虚拟标签置顶 + 实际被搜索频道的真实标签（去重）
            available_tags: list[str] = []
            virtual_tags: list[str] = []
            target_channel_id = None
            if request.channel_ids and len(request.channel_ids) == 1:
                target_channel_id = request.channel_ids[0]
                if cache_service_instance:
                    if has_mapping:
                        mappings_for_tags = channel_mappings_config.get(
                            target_channel_id, []
                        )
                        virtual_tags = [
                            m["tag_name"] for m in mappings_for_tags
                        ]

                    # 从实际搜索的频道集合聚合真实标签
                    real_tag_names: list[str] = []
                    seen_tag_names: set[str] = set()
                    channels_to_scan = (
                        searched_channel_ids
                        if searched_channel_ids
                        else {target_channel_id}
                    )
                    all_channels_cache = cache_service_instance.get_indexed_channels()
                    for ch in all_channels_cache:
                        if ch.id in channels_to_scan:
                            for tag in ch.available_tags:
                                if tag.name not in seen_tag_names:
                                    seen_tag_names.add(tag.name)
                                    real_tag_names.append(tag.name)

                    available_tags = virtual_tags + real_tag_names

            # 获取 Banner 轮播列表（复用同一 session）
            banner_carousel = []
            banner_service = BannerService(session)
            banners = await banner_service.get_active_banners(
                channel_id=target_channel_id
            )
            banner_carousel = [
                BannerItem(
                    thread_id=banner.thread_id,
                    title=banner.title,
                    cover_image_url=banner.cover_image_url,
                    channel_id=banner.channel_id if banner.channel_id else 0,
                )
                for banner in banners
            ]

            # 读取未读更新数量（复用同一 session）
            unread_count = 0
            try:
                if user_id is not None:
                    follow_service = FollowService(session)
                    unread_count = await follow_service.get_unread_count(
                        user_id=user_id
                    )
            except Exception:
                unread_count = 0

        return SearchResponse(
            total=total_threads,
            limit=request.limit,
            offset=len(exclude_thread_ids),
            results=results,
            available_tags=available_tags,
            virtual_tags=virtual_tags,
            banner_carousel=banner_carousel,
            unread_count=unread_count,
        )
    except Exception as e:
        # 生产环境中应使用 logger.exception
        print(f"搜索时发生内部错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="执行搜索时发生内部错误",
        )
