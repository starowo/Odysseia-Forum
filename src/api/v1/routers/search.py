from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.search.cog import Search
from src.search.qo.thread_search import ThreadSearchQuery
from src.search.search_service import SearchService
from config.config_service import ConfigService
from src.shared.enum.search_config_type import SearchConfigType, SearchConfigDefaults
from ..dependencies.security import get_api_key
from ..schemas.search import SearchRequest, SearchResponse, ThreadDetail
from ..schemas.search.author import AuthorDetail

# 全局变量，将在应用启动时由 bot_main.py 注入
search_cog_instance: Search | None = None
async_session_factory: async_sessionmaker | None = None

router = APIRouter(
    prefix="/search", tags=["帖子搜索"], dependencies=[Depends(get_api_key)]
)


@router.post("/", response_model=SearchResponse, summary="执行帖子搜索")
async def execute_search(request: SearchRequest):
    """
    根据指定的条件搜索帖子，并返回包含作者信息的分页结果。

    - request: 搜索请求参数，包含所有搜索条件
    - return: 分页的搜索结果，包含帖子列表和总数
    """
    if not search_cog_instance or not async_session_factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search 服务尚未初始化",
        )

    query_object = ThreadSearchQuery(
        channel_ids=request.channel_ids,
        include_tags=request.include_tags,
        exclude_tags=request.exclude_tags,
        tag_logic=request.tag_logic,
        keywords=request.keywords,
        exclude_keywords=request.exclude_keywords,
        exclude_keyword_exemption_markers=request.exclude_keyword_exemption_markers,
        include_authors=request.include_authors,
        exclude_authors=request.exclude_authors,
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
        async with async_session_factory() as session:
            repo = SearchService(session, search_cog_instance.tag_service)
            config_repo = ConfigService(session)

            total_disp_conf = await config_repo.get_search_config(
                SearchConfigType.TOTAL_DISPLAY_COUNT
            )
            ucb_factor_conf = await config_repo.get_search_config(
                SearchConfigType.UCB1_EXPLORATION_FACTOR
            )
            strength_conf = await config_repo.get_search_config(
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

            threads, total_threads = await repo.search_threads_with_count(
                query_object,
                request.offset,
                request.limit,
                total_display_count,
                exploration_factor,
                strength_weight,
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
                thumbnail_url=thread.thumbnail_url,
                tags=[tag.name for tag in thread.tags],
            )
            results.append(thread_detail)

        return SearchResponse(
            total=total_threads,
            limit=request.limit,
            offset=request.offset,
            results=results,
        )
    except Exception as e:
        # 生产环境中应使用 logger.exception
        print(f"搜索时发生内部错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="执行搜索时发生内部错误",
        )
