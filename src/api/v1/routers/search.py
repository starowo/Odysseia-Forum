from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.search.cog import Search
from src.search.qo.thread_search import ThreadSearchQuery
from src.search.search_service import SearchService
from config.config_service import ConfigService
from src.shared.enum.search_config_type import SearchConfigType, SearchConfigDefaults
from src.shared.keyword_parser import KeywordParser
from ..dependencies.security import require_auth, get_current_user
from ..schemas.search import SearchRequest, SearchResponse, ThreadDetail
from ..schemas.search.author import AuthorDetail
from ..schemas.banner import BannerItem
from src.core.cache_service import CacheService
from src.banner.banner_service import BannerService
from ThreadManager.services.follow_service import FollowService
from typing import Dict, Any

# 全局变量，将在应用启动时由 bot_main.py 注入
search_cog_instance: Search | None = None
async_session_factory: async_sessionmaker | None = None
config_service_instance: ConfigService | None = None
cache_service_instance: CacheService | None = None

router = APIRouter(
    prefix="/search", tags=["帖子搜索"], dependencies=[Depends(require_auth)]
)


@router.post("/", response_model=SearchResponse, summary="执行帖子搜索")
async def execute_search(request: SearchRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    根据指定的条件搜索帖子，并返回包含作者信息的分页结果。

    - request: 搜索请求参数，包含所有搜索条件
    - return: 分页的搜索结果，包含帖子列表和总数
    """
    if (
        not search_cog_instance
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
        author_name, parsed_include_keywords, parsed_exclude_keywords, remaining_keywords = KeywordParser.parse(sanitized_keywords)
    
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

    # 将字符串channel_ids转换为整数
    channel_ids_int = None
    if request.channel_ids:
        channel_ids_int = [int(cid) for cid in request.channel_ids]

    query_object = ThreadSearchQuery(
        channel_ids=channel_ids_int,
        include_tags=request.include_tags,
        exclude_tags=request.exclude_tags,
        tag_logic=request.tag_logic,
        keywords=final_keywords,
        exclude_keywords=final_exclude_keywords if final_exclude_keywords else None,
        exclude_keyword_exemption_markers=request.exclude_keyword_exemption_markers,
        include_authors=request.include_authors,
        exclude_authors=request.exclude_authors,
        author_name=author_name,  # 使用解析出的作者名
        created_after=request.created_after,
        created_before=request.created_before,
        active_after=request.active_after,
        active_before=request.active_before,
        reaction_count_range=request.reaction_count_range,
        reply_count_range=request.reply_count_range,
        sort_method=request.sort_method,
        sort_order=request.sort_order,
        custom_base_sort=request.custom_base_sort,
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

        results = []
        for thread in threads:
            # 手动创建 ThreadDetail 对象，确保字段正确映射
            thread_detail = ThreadDetail(
                thread_id=thread.thread_id,
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
            )
            results.append(thread_detail)

        # 如果是单频道搜索，返回该频道的可用标签
        available_tags = []
        target_channel_id = None
        if request.channel_ids and len(request.channel_ids) == 1:
            target_channel_id = request.channel_ids[0]
            if cache_service_instance:
                all_channels = cache_service_instance.get_indexed_channels()
                target_channel = next(
                    (ch for ch in all_channels if ch.id == target_channel_id),
                    None,
                )
                if target_channel:
                    available_tags = [tag.name for tag in target_channel.available_tags]

        # 获取Banner轮播列表
        banner_carousel = []
        async with async_session_factory() as session:
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

        # 读取未读更新数量
        unread_count = 0
        try:
            user_id = int(current_user["id"]) if current_user and "id" in current_user else None
            if user_id is not None:
                async with async_session_factory() as session:
                    follow_service = FollowService(session)
                    unread_count = await follow_service.get_unread_count(user_id=user_id)
        except Exception:
            unread_count = 0

        return SearchResponse(
            total=total_threads,
            limit=request.limit,
            offset=len(exclude_thread_ids),
            results=results,
            available_tags=available_tags,
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
