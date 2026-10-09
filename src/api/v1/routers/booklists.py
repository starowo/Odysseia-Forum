"""书单相关路由"""

from shared.tag_error import TagError

import logging
from core.tag_query import load_custom_tags
from typing import Literal, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status


from api.v1.dependencies.security import require_auth
from api.v1.schemas.base import PaginatedResponse
from shared.channel_mapping_utils import ChannelMappingUtils

from datetime import datetime, timezone

from api.v1.schemas.booklist import (
    BooklistCreateResponse,
    BooklistDetail,
    BooklistItemAddResponse,
    BooklistItemDetail,
    BooklistItemsAddRequest,
    BooklistItemsDeleteRequest,
    BooklistItemsSyncRequest,
    BooklistItemUpdateRequest,
    BooklistPublishInfo,
    BooklistPublishRequest,
    BooklistSummary,
    BooklistUpdateResponse,
)
from api.v1.schemas.search.author_detail import AuthorDetail
from api.v1.utils import BooklistItemEnricher
from booklist.booklist_publish_service import BooklistPublishService
from booklist.booklist_service import BooklistService
from core.author_repository import AuthorRepository
from core.booklist_item_repository import BooklistItemRepository
from core.booklist_publish_repository import BooklistPublishRepository
from core.booklist_repository import BooklistRepository
from core.collection_repository import CollectionRepository
from dto.booklist_items_sync_dto import BooklistItemsSyncDTO
from models import Author, BooklistItem
from shared.database import AsyncSessionFactory
from shared.keyword_parser import parse_search_keywords
from shared.request_id import RequestId
from shared.thread_link_parser import ThreadLinkParser
from sqlmodel import func, select
from shared.enum import CollectionType
from core.booklist_sort_constants import DEFAULT_SORT_METHOD, DEFAULT_SORT_ORDER
from shared.enum.booklist_sort_method import BooklistSortMethod
from shared.enum.booklist_sort_order import BooklistSortOrder
from shared.redis_client import RedisManager

# 频道映射配置
channel_mappings_config: Dict[int, List[Dict]] = {}

# 由 api_main.py 注入的书单发布配置
_booklist_publish_base_url: str = ""
_booklist_publish_api_key: str = ""

logger = logging.getLogger(__name__)


def _resolve_sort_params(
    default_sort_method: Optional[str] = None,
    default_sort_order: Optional[str] = None,
    display_type: Optional[int] = None,
) -> tuple[str, str]:
    """
    解析书单排序参数，兼容旧 display_type 字段。

    优先级：新字段 > display_type 转换 > 默认值
    """
    # 如果提供了新字段，直接使用（验证合法性）
    if default_sort_method is not None:
        valid_methods = {m.value for m in BooklistSortMethod}
        if default_sort_method not in valid_methods:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的排序方式: {default_sort_method}. 可选值: {', '.join(sorted(valid_methods))}",
            )
        valid_orders = {o.value for o in BooklistSortOrder}
        if default_sort_order is not None and default_sort_order not in valid_orders:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的排序顺序: {default_sort_order}. 可选值: asc, desc",
            )
        return default_sort_method, default_sort_order or DEFAULT_SORT_ORDER.value

    # 兼容旧 display_type 字段
    if display_type is not None:
        if display_type == 2:
            return BooklistSortMethod.DISPLAY_ORDER.value, BooklistSortOrder.ASC.value
        return BooklistSortMethod.JOIN_TIME.value, BooklistSortOrder.DESC.value

    # 默认值
    return DEFAULT_SORT_METHOD.value, DEFAULT_SORT_ORDER.value


async def _fill_authors_for_booklists(
    session: Any, booklists: List[Any]
) -> Dict[int, Any]:
    """获取书单的作者映射，并在不存在或过期时将其加入到 Redis 待拉取队列"""
    owner_ids = list(set(b.owner_id for b in booklists if getattr(b, "owner_id", None)))
    if not owner_ids:
        return {}

    author_repo = AuthorRepository(session)
    authors = await author_repo.get_authors_by_ids(owner_ids)
    author_map = {a.id: a for a in authors}

    client = RedisManager.get_client()
    now = datetime.now(timezone.utc)

    for owner_id in owner_ids:
        author = author_map.get(owner_id)
        needs_fetch = False
        if not author:
            needs_fetch = True
        else:
            last_updated = getattr(author, "last_updated", None)
            if last_updated:
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                if (now - last_updated).days >= 7:
                    needs_fetch = True
            else:
                needs_fetch = True

        if needs_fetch:
            try:
                await client.sadd("author_fetch_queue", str(owner_id))  # type: ignore
            except Exception:
                logger.warning(
                    "将 owner_id=%s 加入 author_fetch_queue 失败",
                    owner_id,
                    exc_info=True,
                )

    return author_map


async def _fill_fallback_covers(session: Any, booklists: List[Any]) -> Dict[int, str]:
    """为无自定义封面的书单批量获取 fallback 封面

    取书单内最近加入的帖子的第一张 thumbnail；避免前端为每个无封面书单
    单独调用 /item/list/page/{booklist_id} 的 N+1 模式。
    """
    missing_ids = [
        b.id for b in booklists if b.id is not None and not b.cover_image_url
    ]
    if not missing_ids:
        return {}
    item_repo = BooklistItemRepository(session)
    return await item_repo.get_fallback_covers(missing_ids)


def _apply_anonymous_author(
    detail: BooklistSummary, booklist: Any, current_user_id: int, author_map: dict
):
    if getattr(booklist, "is_anonymous", False):
        if current_user_id != booklist.owner_id:
            detail.owner_id = 0
        detail.author = AuthorDetail(
            id=0,
            name="匿名用户",
            global_name=None,
            display_name="匿名用户",
            avatar_url="https://cdn.discordapp.com/embed/avatars/0.png",
        )
    elif booklist.owner_id in author_map:
        detail.author = AuthorDetail.model_validate(
            author_map[booklist.owner_id], from_attributes=True
        )


router = APIRouter(prefix="/booklist", tags=["书单"])


@router.post("/save", summary="创建书单", response_model=BooklistCreateResponse)
async def create_booklist(
    title: str,
    description: Optional[str] = None,
    cover_image_url: Optional[str] = None,
    is_public: bool = True,
    is_anonymous: bool = False,
    display_type: Optional[int] = Query(
        None,
        deprecated=True,
        description="已废弃，请使用 default_sort_method + default_sort_order",
    ),
    default_sort_method: Optional[str] = Query(None, description="默认排序方式"),
    default_sort_order: Optional[str] = Query(None, description="默认排序顺序"),
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    创建新书单

    - title: 书单标题（必填）
    - description: 书单简介（可选）
    - cover_image_url: 封面图 URL（可选）
    - is_public: 是否公开，默认为 True
    - is_anonymous: 是否匿名，默认为 False
    - default_sort_method: 默认排序方式，默认为 join_time。可选值:
        - "hot": Reddit Hot 算法 — score = log10(max(1, reaction_count)) + created_at_epoch / time_decay
        - "created_at": 按发帖时间排序
        - "reaction_count": 按点赞数排序
        - "reply_count": 按回复数排序
        - "collection_count": 按收藏数排序
        - "last_active_at": 按最后发言时间排序
        - "join_time": 按加入书单时间排序 (默认)
        - "display_order": 按作者自定义排序权重排序
    - default_sort_order: 默认排序顺序，默认为 desc
    """
    try:
        user_id = int(current_user["id"])
        sort_method, sort_order = _resolve_sort_params(
            default_sort_method=default_sort_method,
            default_sort_order=default_sort_order,
            display_type=display_type,
        )

        async with AsyncSessionFactory() as session:
            service = BooklistRepository(session)
            booklist = await service.create_booklist(
                owner_id=user_id,
                title=title,
                description=description,
                cover_image_url=cover_image_url,
                is_public=is_public,
                is_anonymous=is_anonymous,
                default_sort_method=sort_method,
                default_sort_order=sort_order,
            )

            if booklist.id is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="书单创建失败，未获取到ID",
                )
            result = BooklistCreateResponse(
                booklist_id=booklist.id,
                title=booklist.title,
                created_at=booklist.created_at,
            )
        return result

    except Exception as e:
        logger.error(f"创建书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建书单失败"
        )


@router.get(
    "/list/page",
    summary="分页搜索公开书单",
    response_model=PaginatedResponse[BooklistSummary],
)
async def list_public_booklists(
    include_tags: list[str] | None = Query(
        default=None,
        description="包含的标签标准名或别名；标准名完整匹配，别名完整匹配且忽略大小写；多个值使用重复参数，按 tag_logic 组合；与 ID 筛选共同生效",
    ),
    exclude_tags: list[str] | None = Query(
        default=None,
        description="排除的标签标准名或别名；别名完整匹配且忽略大小写，命中任一即排除；只匹配书单自身绑定",
    ),
    include_tag_ids: list[RequestId] | None = Query(
        default=None,
        description="按书单自身绑定的标签内部 ID 筛选，不继承单内帖子的标签；多个值使用重复查询参数，接受十进制字符串或整数；按 tag_logic 组合",
    ),
    exclude_tag_ids: list[RequestId] | None = Query(
        default=None,
        description="排除自身绑定任一指定标签的书单；传标签内部 ID，多个值使用重复查询参数，接受十进制字符串或整数",
    ),
    tag_logic: Literal["and", "or"] = Query(
        default="and",
        description="包含标签的组合逻辑：and 要求全部命中，or 要求至少命中一个；分别作用于 include_tags 和 include_tag_ids，两组条件共同生效，不改变排除条件",
    ),
    owner_id: Optional[int] = Query(None, description="创建者用户ID"),
    keywords: Optional[str] = Query(None, description="模糊搜索关键词，匹配标题和描述"),
    included_thread_id: Optional[int] = Query(
        None, description="筛选包含指定帖子ID的书单"
    ),
    is_tournament: Optional[bool] = Query(
        None, description="筛选赛事书单（true=仅赛事，false=仅非赛事，不传=全部）"
    ),
    search_by_collect: Optional[bool] = Query(
        None, description="从当前用户收藏的书单中筛选"
    ),
    sort_method: int = Query(
        4,
        description="排序方法: 1-书单内帖子数量, 2-被浏览次数,3-被收藏次数,4-创建时间,5-最后更新时间",
    ),
    sort_order: str = Query(
        "desc", description="排序顺序: 'asc'(升序) 或 'desc'(降序)"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="每次请求返回的数量 (范围: 1-100)",
    ),
    offset: int = Query(default=0, ge=0, description="结果的偏移量，从0开始"),
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    分页搜索公开书单

    - owner_id: 按创建者筛选
    - keywords: 模糊搜索关键词(标题和简介)
    - included_thread_id: 筛选包含指定帖子ID的书单
    - is_tournament: 筛选赛事书单
    - sort_method: 排序方式 (1: 书单内帖子数, 2: 浏览数, 3: 收藏数, 4: 创建时间, 5: 更新时间)
    - sort_order: 排序顺序 ('asc' 或 'desc')
    - limit: 返回数量
    - offset: 偏移量
    """
    try:
        # 当 search_by_collect 为真时，获取当前用户ID作为 collected_by_user_id
        collected_by_user_id = None
        if search_by_collect:
            collected_by_user_id = int(current_user["id"])

        # 解析高级搜索关键词（author:Name, "精确短语", -排除词）
        parsed_author_name, final_keywords, final_exclude_keywords = (
            parse_search_keywords(keywords, None)
        )

        async with AsyncSessionFactory() as session:
            # 若解析出 author:Name，查询 Author 表获取匹配的 owner_id 列表
            resolved_owner_ids: list[int] | None = None
            if parsed_author_name:
                search_pattern = f"%{parsed_author_name}%"
                author_stmt = select(Author.id).where(
                    (func.lower(Author.name) == parsed_author_name.lower())  # type: ignore
                    | (Author.global_name.like(search_pattern))  # type: ignore
                    | (Author.display_name.like(search_pattern))  # type: ignore
                )
                author_rows = await session.execute(author_stmt)
                matched = set(author_rows.scalars().all())
                if matched:
                    if owner_id is not None:
                        resolved_owner_ids = list(matched & {owner_id})
                    else:
                        resolved_owner_ids = list(matched)
                else:
                    # 作者未找到，用哨兵值确保空结果
                    resolved_owner_ids = [-1]

            service = BooklistRepository(session)
            booklists, total = await service.list_booklists(
                include_tags=include_tags,
                exclude_tags=exclude_tags,
                include_tag_ids=include_tag_ids,
                exclude_tag_ids=exclude_tag_ids,
                tag_logic=tag_logic,
                owner_id=owner_id if resolved_owner_ids is None else None,
                is_public=True,  # 强制只搜索公开书单
                is_tournament=is_tournament,
                keywords=final_keywords,
                exclude_keywords=final_exclude_keywords,
                owner_ids=resolved_owner_ids,
                included_thread_id=included_thread_id,
                collected_by_user_id=collected_by_user_id,
                sort_method=sort_method,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

            # 检查收藏状态
            collected_booklist_ids = set()
            user_id = int(current_user["id"])
            if user_id and booklists:
                booklist_ids = [b.id for b in booklists if b.id is not None]
                collection_service = CollectionRepository(session)
                collected_booklist_ids = (
                    await collection_service.get_collected_target_ids(
                        user_id, CollectionType.BOOKLIST, booklist_ids
                    )
                )

            # 获取书单创建者信息
            author_map = await _fill_authors_for_booklists(session, booklists)
            custom_tag_map = await load_custom_tags(
                session, "booklist", [b.id for b in booklists]
            )

            # 为无自定义封面的书单批量获取 fallback 封面
            fallback_covers = await _fill_fallback_covers(session, booklists)

            results = []
            for b in booklists:
                summary = BooklistSummary.model_validate(b, from_attributes=True)
                summary.custom_tags = custom_tag_map.get(b.id, [])
                _apply_anonymous_author(summary, b, user_id, author_map)

                if b.id in collected_booklist_ids:
                    summary.collected_flag = True
                if not summary.cover_image_url and b.id in fallback_covers:
                    summary.cover_image_url = fallback_covers[b.id]
                results.append(summary)

        return PaginatedResponse(
            total=total, limit=limit, offset=offset, results=results
        )

    except TagError as e:
        raise HTTPException(status_code=e.status, detail=e.detail) from e
    except Exception as e:
        logger.error(f"列出公开书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="列出公开书单失败"
        )


@router.get(
    "/my/list/page",
    summary="分页搜索我的书单",
    response_model=PaginatedResponse[BooklistSummary],
)
async def list_my_booklists(
    include_tags: list[str] | None = Query(
        default=None,
        description="包含的标签标准名或别名；标准名完整匹配，别名完整匹配且忽略大小写；多个值使用重复参数，按 tag_logic 组合；与 ID 筛选共同生效",
    ),
    exclude_tags: list[str] | None = Query(
        default=None,
        description="排除的标签标准名或别名；别名完整匹配且忽略大小写，命中任一即排除；只匹配书单自身绑定",
    ),
    include_tag_ids: list[RequestId] | None = Query(
        default=None,
        description="按书单自身绑定的标签内部 ID 筛选，不继承单内帖子的标签；多个值使用重复查询参数，接受十进制字符串或整数；按 tag_logic 组合",
    ),
    exclude_tag_ids: list[RequestId] | None = Query(
        default=None,
        description="排除自身绑定任一指定标签的书单；传标签内部 ID，多个值使用重复查询参数，接受十进制字符串或整数",
    ),
    tag_logic: Literal["and", "or"] = Query(
        default="and",
        description="包含标签的组合逻辑：and 要求全部命中，or 要求至少命中一个；分别作用于 include_tags 和 include_tag_ids，两组条件共同生效，不改变排除条件",
    ),
    is_public: Optional[bool] = Query(None, description="筛选公开状态 (不传则不筛选)"),
    keywords: Optional[str] = Query(None, description="模糊搜索关键词，匹配标题和描述"),
    collect_by_current_user: Optional[bool] = Query(
        None, description="从当前用户收藏的书单中筛选"
    ),
    create_by_current_user: Optional[bool] = Query(
        None, description="从当前用户创建的书单中筛选"
    ),
    sort_method: int = Query(
        4,
        description="排序方法: 1-帖子数, 2-浏览数, 3-收藏数, 4-创建时间, 5-最后更新时间",
    ),
    sort_order: str = Query(
        "desc", description="排序顺序: 'asc'(升序) 或 'desc'(降序)"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="每次请求返回的数量 (范围: 1-100)",
    ),
    offset: int = Query(default=0, ge=0, description="结果的偏移量，从0开始"),
    mark_thread_id: Optional[int] = Query(
        None,
        description="标记帖子ID：传入后为每个书单标注是否包含该帖子（不过滤结果集），配合is_marked字段使用",
    ),
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    分页搜索我的书单（登录用户创建的书单）

    - is_public: 按公开状态筛选
    - keywords: 模糊搜索关键词(标题和简介)
    - sort_method: 排序方式 (1: 帖子数, 2: 浏览数, 3: 收藏数, 4: 创建时间, 5: 更新时间, 6-收藏时间 collect_by_current_user=true 时可用,)
    - sort_order: 排序顺序 ('asc' 或 'desc')
    - limit: 返回数量
    - offset: 偏移量
    """
    try:
        user_id = int(current_user["id"])
        owner_id = None
        collected_by_user_id = None

        if create_by_current_user:
            owner_id = user_id
        if collect_by_current_user:
            collected_by_user_id = user_id

        # 解析高级搜索关键词（author:Name, "精确短语", -排除词）
        parsed_author_name, final_keywords, final_exclude_keywords = (
            parse_search_keywords(keywords, None)
        )

        async with AsyncSessionFactory() as session:
            # 若解析出 author:Name，查询 Author 表获取匹配的 owner_id 列表
            resolved_owner_ids: list[int] | None = None
            if parsed_author_name:
                search_pattern = f"%{parsed_author_name}%"
                author_stmt = select(Author.id).where(
                    (func.lower(Author.name) == parsed_author_name.lower())  # type: ignore
                    | (Author.global_name.like(search_pattern))  # type: ignore
                    | (Author.display_name.like(search_pattern))  # type: ignore
                )
                author_rows = await session.execute(author_stmt)
                matched = set(author_rows.scalars().all())
                if matched:
                    if owner_id is not None:
                        resolved_owner_ids = list(matched & {owner_id})
                    else:
                        resolved_owner_ids = list(matched)
                else:
                    # 作者未找到，用哨兵值确保空结果
                    resolved_owner_ids = [-1]

            service = BooklistRepository(session)
            booklists, total = await service.list_booklists(
                include_tags=include_tags,
                exclude_tags=exclude_tags,
                include_tag_ids=include_tag_ids,
                exclude_tag_ids=exclude_tag_ids,
                tag_logic=tag_logic,
                owner_id=owner_id if resolved_owner_ids is None else None,
                is_public=is_public,
                keywords=final_keywords,
                exclude_keywords=final_exclude_keywords,
                owner_ids=resolved_owner_ids,
                collected_by_user_id=collected_by_user_id,
                sort_method=sort_method,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

            # 检查收藏状态
            collected_booklist_ids = set()
            user_id = int(current_user["id"])
            if user_id and booklists:
                booklist_ids = [b.id for b in booklists if b.id is not None]
                collection_service = CollectionRepository(session)
                collected_booklist_ids = (
                    await collection_service.get_collected_target_ids(
                        user_id, CollectionType.BOOKLIST, booklist_ids
                    )
                )

            # 查询标记帖子在哪些书单中存在
            marked_booklist_ids = set()
            if mark_thread_id is not None and booklists:
                booklist_ids = [b.id for b in booklists if b.id is not None]
                stmt = select(BooklistItem.booklist_id).where(
                    BooklistItem.thread_id == mark_thread_id,
                    BooklistItem.booklist_id.in_(booklist_ids),  # type: ignore
                )
                rows = await session.execute(stmt)
                marked_booklist_ids = set(rows.scalars().all())

            # 获取书单创建者信息
            author_map = await _fill_authors_for_booklists(session, booklists)
            custom_tag_map = await load_custom_tags(
                session, "booklist", [b.id for b in booklists]
            )

            # 为无自定义封面的书单批量获取 fallback 封面
            fallback_covers = await _fill_fallback_covers(session, booklists)

            results = []
            for b in booklists:
                summary = BooklistSummary.model_validate(b, from_attributes=True)
                summary.custom_tags = custom_tag_map.get(b.id, [])
                _apply_anonymous_author(summary, b, user_id, author_map)

                if b.id in collected_booklist_ids:
                    summary.collected_flag = True
                if b.id in marked_booklist_ids:
                    summary.is_marked = True
                if not summary.cover_image_url and b.id in fallback_covers:
                    summary.cover_image_url = fallback_covers[b.id]
                results.append(summary)

        return PaginatedResponse(
            total=total, limit=limit, offset=offset, results=results
        )
    except TagError as e:
        raise HTTPException(status_code=e.status, detail=e.detail) from e
    except Exception as e:
        logger.error(f"列出我的书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="列出用户书单失败"
        )


@router.get(
    "/detail/{booklist_id}", summary="获取书单详情", response_model=BooklistDetail
)
async def get_booklist(
    booklist_id: int, current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    根据ID获取书单详情

    - booklist_id: 书单ID
    """
    try:
        async with AsyncSessionFactory() as session:
            service = BooklistRepository(session)
            booklist = await service.get_booklist(booklist_id)
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )
            # 权限检查：非公开书单只有所有者可以查看
            if not booklist.is_public and booklist.owner_id != int(current_user["id"]):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此书单"
                )

            # 检查当前用户是否收藏了该书单
            collected_flag = False
            user_id = int(current_user["id"])
            if booklist_id is not None:
                collection_service = CollectionRepository(session)
                collected_ids = await collection_service.get_collected_target_ids(
                    user_id, CollectionType.BOOKLIST, [booklist_id]
                )
                collected_flag = booklist_id in collected_ids

            # 获取书单创建者信息
            author_map = await _fill_authors_for_booklists(session, [booklist])
            detail = BooklistDetail.model_validate(booklist, from_attributes=True)
            detail.custom_tags = (
                await load_custom_tags(session, "booklist", [booklist.id])
            ).get(booklist.id, [])
            detail.collected_flag = collected_flag
            _apply_anonymous_author(detail, booklist, user_id, author_map)

            # 查询发布信息
            publish_repo = BooklistPublishRepository(session)
            record = await publish_repo.get_by_booklist(booklist_id)
            if record:
                detail.publish_info = BooklistPublishInfo(
                    guild_id=record.guild_id,
                    thread_id=record.thread_id,
                    thread_url=f"https://discord.com/channels/{record.guild_id}/{record.thread_id}",
                    message_id=record.message_id,
                    message_url=record.message_url,
                    published_at=record.created_at,
                )

            # 增加查看次数（放最后，避免 commit 后 booklist 过期导致 MissingGreenlet）
            await service.increment_view_count(booklist_id)
            return detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取书单详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取书单详情失败"
        )


@router.put(
    "/update/{booklist_id}", summary="更新书单", response_model=BooklistUpdateResponse
)
async def update_booklist(
    booklist_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    cover_image_url: Optional[str] = None,
    is_public: Optional[bool] = None,
    is_anonymous: Optional[bool] = None,
    display_type: Optional[int] = Query(
        None,
        deprecated=True,
        description="已废弃，请使用 default_sort_method + default_sort_order",
    ),
    default_sort_method: Optional[str] = Query(None, description="默认排序方式"),
    default_sort_order: Optional[str] = Query(None, description="默认排序顺序"),
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    更新书单信息

    - booklist_id: 书单ID
    - title: 新标题（可选）
    - description: 新简介（可选）
    - cover_image_url: 新封面图URL（可选）
    - is_public: 是否公开（可选）
    - is_anonymous: 是否匿名（可选）
    - default_sort_method: 默认排序方式（可选）。可选值:
        - "hot": Reddit Hot 算法 — score = log10(max(1, reaction_count)) + created_at_epoch / time_decay
        - "created_at": 按发帖时间排序
        - "reaction_count": 按点赞数排序
        - "reply_count": 按回复数排序
        - "collection_count": 按收藏数排序
        - "last_active_at": 按最后发言时间排序
        - "join_time": 按加入书单时间排序
        - "display_order": 按作者自定义排序权重排序
    - default_sort_order: 默认排序顺序（可选）
    """
    try:
        user_id = int(current_user["id"])
        sort_method, sort_order = _resolve_sort_params(
            default_sort_method=default_sort_method,
            default_sort_order=default_sort_order,
            display_type=display_type,
        )

        async with AsyncSessionFactory() as session:
            service = BooklistRepository(session)
            # 检查权限
            booklist = await service.get_booklist(booklist_id)
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )
            if booklist.owner_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此书单"
                )

            updated = await service.update_booklist(
                booklist_id=booklist_id,
                title=title,
                description=description,
                cover_image_url=cover_image_url,
                is_public=is_public,
                is_anonymous=is_anonymous,
                default_sort_method=sort_method,
                default_sort_order=sort_order,
            )
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )

            if not updated.id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="书单更新失败，未获取到ID",
                )
            result = BooklistUpdateResponse(
                booklist_id=updated.id,
                title=updated.title,
            )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新书单失败"
        )


@router.delete("/delete/{booklist_id}", summary="删除书单")
async def delete_booklist(
    booklist_id: int, current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    删除书单及其所有关联项

    - booklist_id: 书单ID
    """
    try:
        user_id = int(current_user["id"])
        async with AsyncSessionFactory() as session:
            service = BooklistRepository(session)
            # 检查权限
            booklist = await service.get_booklist(booklist_id)
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )
            if booklist.owner_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="无权删除此书单"
                )

            # 删除前保存是否存在发布记录，供本地提交后通知外部服务。
            publish_repo = BooklistPublishRepository(session)
            publish_record = await publish_repo.get_by_booklist(booklist_id)
            success = await service.delete_booklist(booklist_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )

            # 仅已发布书单需要清理其在所有帖子中的外部消息。
            if publish_record:
                publish_service = BooklistPublishService(
                    session,
                    base_url=_booklist_publish_base_url,
                    api_key=_booklist_publish_api_key,
                )
                publish_service.schedule_unpublish(booklist_id)

        return {"message": "书单删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除书单失败"
        )


@router.post(
    "/publish/{booklist_id}", summary="发布书单到 Discord", response_model=dict
)
async def publish_booklist(
    booklist_id: int,
    request: BooklistPublishRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    发布（或更新）书单到指定的 Discord 讨论帖。

    若该书单已发布到同一帖，则更新既有消息（幂等）。
    接口立即返回，后台异步调用 discord-featured-bot 完成实际发布。
    """
    # 检查服务是否已配置
    if not _booklist_publish_base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="书单发布服务未配置",
        )

    try:
        user_id = int(current_user["id"])
        discord_user_id = int(current_user["id"])

        # 解析 thread_url → guild_id + thread_id
        guild_id, thread_id = ThreadLinkParser.parse_thread_url(request.thread_url)

        async with AsyncSessionFactory() as session:
            # 权限校验
            booklist_repo = BooklistRepository(session)
            booklist = await booklist_repo.get_booklist(booklist_id)
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )
            if booklist.owner_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="无权发布此书单"
                )

            service = BooklistPublishService(
                session,
                base_url=_booklist_publish_base_url,
                api_key=_booklist_publish_api_key,
            )
            await service.publish(booklist_id, guild_id, thread_id, discord_user_id)

        return {
            "message": "书单发布请求已提交",
            "publish_status": 1,  # PENDING
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"发布书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="发布书单失败"
        )


@router.delete("/publish/{booklist_id}", summary="取消发布书单")
async def unpublish_booklist(
    booklist_id: int,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    取消发布书单，删除所有发布记录。
    """
    try:
        user_id = int(current_user["id"])
        async with AsyncSessionFactory() as session:
            # 权限校验
            booklist_repo = BooklistRepository(session)
            booklist = await booklist_repo.get_booklist(booklist_id)
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )
            if booklist.owner_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="无权取消发布此书单"
                )

            service = BooklistPublishService(
                session,
                base_url=_booklist_publish_base_url,
                api_key=_booklist_publish_api_key,
            )
            await service.unpublish(booklist_id)

        return {"message": "书单已取消发布", "publish_status": 0}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消发布书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="取消发布书单失败"
        )


@router.post(
    "/item/add/{booklist_id}",
    summary="向书单批量添加帖子",
    response_model=List[BooklistItemAddResponse],
)
async def add_threads_to_booklist(
    booklist_id: int,
    request: BooklistItemsAddRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    向书单批量添加帖子

    - **booklist_id**: 书单ID
    - **request body**: 包含一个`items`列表，每个元素包含:
        - **thread_id**: 帖子ID (必填)，支持整数或数字字符串，范围为 1 至 9223372036854775807
        - **comment**: 推荐语 (可选)
        - **display_order**: 排序序号 (可选)

    每个帖子 ID 应作为独立的 items 条目提交。任一 ID 非法时整批返回 HTTP 422，
    detail[].msg 提供中文提示，detail[].loc 定位具体条目；超范围时提示检查遗漏逗号。
    """
    try:
        user_id = int(current_user["id"])
        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
            added_items = await service.add_threads(
                user_id=user_id,
                booklist_id=booklist_id,
                items=request.items,
            )

            response_items = []
            for item in added_items:
                if item.id is None:
                    logger.error(f"书单项 {item} 创建后未获得ID。")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="部分书单项创建失败。",
                    )
                response_items.append(
                    BooklistItemAddResponse(
                        booklist_item_id=item.id,
                        booklist_id=item.booklist_id,
                        thread_id=item.thread_id,
                        display_order=item.display_order,
                    )
                )
        return response_items

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量添加帖子到书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量添加帖子到书单失败",
        )


@router.delete("/item/delete/{booklist_id}", summary="从书单批量移除帖子")
async def remove_threads_from_booklist(
    booklist_id: int,
    request: BooklistItemsDeleteRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    从书单批量移除帖子

    - **booklist_id**: 书单ID
    - **request body**: 包含一个`thread_ids`列表，每个元素为要移除的帖子ID
    """
    try:
        user_id = int(current_user["id"])
        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
            deleted_count = await service.remove_threads(
                user_id=user_id,
                booklist_id=booklist_id,
                thread_ids=request.thread_ids,  # type: ignore
            )

        return {"message": f"成功从书单移除 {deleted_count} 个帖子"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从书单批量移除帖子失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="从书单批量移除帖子失败",
        )


@router.post(
    "/item/sync",
    summary="批量修改帖子在多个书单中的存在性",
    response_model=BooklistItemsSyncDTO,
)
async def sync_thread_in_booklists(
    request: BooklistItemsSyncRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    批量修改/覆盖一个帖子在用户拥有的多个书单中的存在性。

    - **thread_id**: 帖子ID
    - **scope_booklist_ids**: 操作范围（必须全是当前用户拥有的书单）
    - **target_booklist_ids**: 操作后应包含该帖子的书单（必须是 scope 的子集）
    - **comment**: 应用于目标书单项的推荐语（可选）
    """
    try:
        user_id = int(current_user["id"])
        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
            result = await service.sync_thread_in_booklists(
                user_id=user_id,
                thread_id=request.thread_id,
                scope_booklist_ids=request.scope_booklist_ids,
                target_booklist_ids=request.target_booklist_ids,
                comment=request.comment,
            )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量同步帖子的书单状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步失败: {e}",
        )


@router.get(
    "/item/list/page/{booklist_id}",
    summary="分页获取书单内的帖子详情",
    response_model=PaginatedResponse[BooklistItemDetail],
)
async def get_booklist_items(
    booklist_id: int,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="每次请求返回的数量 (范围: 1-100)",
    ),
    offset: int = Query(default=0, ge=0, description="结果的偏移量，从0开始"),
    sort_method: Optional[str] = Query(
        None,
        description="排序方式: hot(热门-Reddit Hot算法), created_at(发帖时间), "
        "reaction_count(点赞数), reply_count(回复数), collection_count(收藏数), "
        "last_active_at(最后发言时间), join_time(加入书单时间), "
        "display_order(作者自定义排序)。不传则使用书单默认排序",
    ),
    sort_order: Optional[str] = Query(
        None,
        description="排序顺序: asc(升序) 或 desc(降序)。不传则使用书单默认排序",
    ),
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    分页获取书单内的帖子详情

    - booklist_id: 书单ID
    - limit: 返回数量
    - offset: 偏移量
    - sort_method: 排序方式（可选），覆盖书单默认排序
    - sort_order: 排序顺序（可选），覆盖书单默认排序
    """
    try:
        async with AsyncSessionFactory() as session:
            service = BooklistRepository(session)
            # 检查权限
            booklist = await service.get_booklist(booklist_id)
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )
            if not booklist.is_public and booklist.owner_id != int(current_user["id"]):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此书单内容"
                )

            # 解析排序参数：用户传参 > 书单默认 > 系统默认
            if sort_method is not None:
                valid_methods = {m.value for m in BooklistSortMethod}
                if sort_method not in valid_methods:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"无效的排序方式: {sort_method}. 可选值: {', '.join(sorted(valid_methods))}",
                    )
                resolved_method = sort_method
            else:
                resolved_method = (
                    booklist.default_sort_method or DEFAULT_SORT_METHOD.value
                )

            if sort_order is not None:
                if sort_order not in ("asc", "desc"):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"无效的排序顺序: {sort_order}. 可选值: asc, desc",
                    )
                resolved_order = sort_order
            else:
                resolved_order = booklist.default_sort_order or DEFAULT_SORT_ORDER.value

            item_service = BooklistItemRepository(session)
            items, total = await item_service.get_booklist_items_with_details(
                booklist_id=booklist_id,
                default_sort_method=resolved_method,
                default_sort_order=resolved_order,
                limit=limit,
                offset=offset,
            )

            user_id = int(current_user["id"])

            # 预计算全量反向映射 channel_id -> virtual_tags
            channel_to_virtual: Dict[int, List[str]] = {}
            if channel_mappings_config:
                mapping_utils = ChannelMappingUtils(channel_mappings_config)
                channel_to_virtual = mapping_utils.get_all_channel_virtual_tags_map()

            # 更新收藏状态与虚拟标签
            for item in items:
                if item.channel_id in channel_to_virtual:
                    item.virtual_tags = list(set(channel_to_virtual[item.channel_id]))
            await BooklistItemEnricher.enrich(session, user_id, items)

        return PaginatedResponse(total=total, limit=limit, offset=offset, results=items)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取书单内容失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取书单内容失败"
        )


@router.patch(
    "/item/update/{booklist_id}/{thread_id}",
    summary="更新书单内帖子信息",
    response_model=BooklistItemDetail,
)
async def update_booklist_item(
    booklist_id: int,
    thread_id: int,
    update_data: BooklistItemUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    更新书单中的单个项目（帖子）

    - booklist_id: 目标书单的ID
    - thread_id: 目标帖子的ID
    - update_data: 要更新的数据
        - comment: (可选) 新的推荐语/备注
        - display_order: (可选) 新的排序权重
    """
    try:
        user_id = int(current_user["id"])
        async with AsyncSessionFactory() as session:
            # 权限检查
            booklist_service = BooklistRepository(session)
            booklist_item_service = BooklistItemRepository(session)
            booklist = await booklist_service.get_booklist(booklist_id)
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )
            if booklist.owner_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此书单"
                )

            # 更新书单项
            item_service = BooklistItemRepository(session)
            updated_item = await item_service.update_booklist_item(
                booklist_id, thread_id, update_data
            )

            if not updated_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定的帖子不在该书单中",
                )

            # 获取并返回更新后的详细信息
            item_detail = await booklist_item_service.get_booklist_item_detail(
                booklist_id, thread_id
            )
            if not item_detail:
                # This should not happen if the update was successful
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="获取更新后的书单项详情失败",
                )

            # 计算虚拟标签
            channel_to_virtual: Dict[int, List[str]] = {}
            if channel_mappings_config:
                mapping_utils = ChannelMappingUtils(channel_mappings_config)
                channel_to_virtual = mapping_utils.get_all_channel_virtual_tags_map()

            if item_detail.channel_id in channel_to_virtual:
                item_detail.virtual_tags = list(
                    set(channel_to_virtual[item_detail.channel_id])
                )

            await BooklistItemEnricher.enrich(session, user_id, [item_detail])

            return item_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新书单项失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新书单项失败",
        )
