"""书单相关路由"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.v1.dependencies.security import require_auth
from api.v1.schemas.base import PaginatedResponse
from api.v1.schemas.booklist import (
    BooklistCreateResponse,
    BooklistDetail,
    BooklistItemAddResponse,
    BooklistItemDetail,
    BooklistItemsAddRequest,
    BooklistItemsDeleteRequest,
    BooklistItemUpdateRequest,
    BooklistUpdateResponse,
)
from booklist.booklist_item_service import BooklistItemService
from booklist.booklist_service import BooklistService
from collection.cog import CollectionCog
from shared.database import AsyncSessionFactory
from shared.enum.collection_type import CollectionType

logger = logging.getLogger(__name__)

collection_cog_instance: CollectionCog | None = None

router = APIRouter(prefix="/booklist", tags=["书单"])


@router.post("/save", summary="创建书单", response_model=BooklistCreateResponse)
async def create_booklist(
    title: str,
    description: Optional[str] = None,
    cover_image_url: Optional[str] = None,
    is_public: bool = True,
    display_type: int = 1,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    创建新书单

    - title: 书单标题（必填）
    - description: 书单简介（可选）
    - cover_image_url: 封面图 URL（可选）
    - is_public: 是否公开，默认为 True
    - display_type: 展示方式，1=加入时间倒序，2=display_order，默认为1
    """
    try:
        user_id = int(current_user["id"])

        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
            booklist = await service.create_booklist(
                owner_id=user_id,
                title=title,
                description=description,
                cover_image_url=cover_image_url,
                is_public=is_public,
                display_type=display_type,
            )

        if booklist.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="书单创建失败，未获取到ID",
            )
        return BooklistCreateResponse(
            booklist_id=booklist.id,
            title=booklist.title,
            created_at=booklist.created_at,
        )

    except Exception as e:
        logger.error(f"创建书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建书单失败"
        )


@router.get(
    "/list/page",
    summary="分页搜索公开书单",
    response_model=PaginatedResponse[BooklistDetail],
)
async def list_public_booklists(
    owner_id: Optional[int] = Query(None, description="创建者用户ID"),
    keywords: Optional[str] = Query(None, description="模糊搜索关键词，匹配标题和描述"),
    included_thread_id: Optional[int] = Query(
        None, description="筛选包含指定帖子ID的书单"
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
    offset: int = Query(default=0, ge=0, description="结果的偏移页，从0开始"),
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    分页搜索公开书单

    - owner_id: 按创建者筛选
    - keywords: 模糊搜索关键词(标题和简介)
    - included_thread_id: 筛选包含指定帖子ID的书单
    - sort_method: 排序方式 (1: 书单内帖子数, 2: 浏览数, 3: 收藏数, 4: 创建时间, 5: 更新时间)
    - sort_order: 排序顺序 ('asc' 或 'desc')
    - limit: 返回数量
    - offset: 偏移页
    """
    try:
        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
            booklists, total = await service.list_booklists(
                owner_id=owner_id,
                is_public=True,  # 强制只搜索公开书单
                keywords=keywords,
                included_thread_id=included_thread_id,
                collected_by_user_id=None,
                sort_method=sort_method,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

        results = [
            BooklistDetail.model_validate(b, from_attributes=True) for b in booklists
        ]
        return PaginatedResponse(
            total=total, limit=limit, offset=offset, results=results
        )

    except Exception as e:
        logger.error(f"列出公开书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="列出公开书单失败"
        )


@router.get(
    "/my/list/page",
    summary="分页搜索我的书单",
    response_model=PaginatedResponse[BooklistDetail],
)
async def list_my_booklists(
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
    offset: int = Query(default=0, ge=0, description="结果的偏移页，从0开始"),
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    分页搜索我的书单（登录用户创建的书单）

    - is_public: 按公开状态筛选
    - keywords: 模糊搜索关键词(标题和简介)
    - sort_method: 排序方式 (1: 帖子数, 2: 浏览数, 3: 收藏数, 4: 创建时间, 5: 更新时间, 6-收藏时间 collect_by_current_user=true 时可用,)
    - sort_order: 排序顺序 ('asc' 或 'desc')
    - limit: 返回数量
    - offset: 偏移页
    """
    try:
        user_id = int(current_user["id"])
        owner_id = None
        collected_by_user_id = None

        if create_by_current_user:
            owner_id = user_id
        if collect_by_current_user:
            collected_by_user_id = user_id

        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
            booklists, total = await service.list_booklists(
                owner_id=owner_id,
                is_public=is_public,
                keywords=keywords,
                collected_by_user_id=collected_by_user_id,
                sort_method=sort_method,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

        # 检查收藏状态
        collected_booklist_ids = set()
        user_id = int(current_user["id"])
        if user_id and booklists and collection_cog_instance:
            booklist_ids = [b.id for b in booklists if b.id is not None]
            async with (
                collection_cog_instance.get_collection_service() as collection_service
            ):
                collected_booklist_ids = (
                    await collection_service.get_collected_target_ids(
                        user_id, CollectionType.BOOKLIST, booklist_ids
                    )
                )

        results = []
        for b in booklists:
            detail = BooklistDetail.model_validate(b, from_attributes=True)
            if b.id in collected_booklist_ids:
                detail.collected_flag = True
            results.append(detail)

        return PaginatedResponse(
            total=total, limit=limit, offset=offset, results=results
        )
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
            service = BooklistService(session)
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
            # 增加查看次数
            await service.increment_view_count(booklist_id)

        return BooklistDetail.model_validate(booklist, from_attributes=True)

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
    display_type: Optional[int] = None,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    更新书单信息

    - booklist_id: 书单ID
    - title: 新标题（可选）
    - description: 新简介（可选）
    - cover_image_url: 新封面图URL（可选）
    - is_public: 是否公开（可选）
    - display_type: 展示方式（可选）
    """
    try:
        user_id = int(current_user["id"])
        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
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
                display_type=display_type,
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
        return BooklistUpdateResponse(
            booklist_id=updated.id,
            title=updated.title,
        )

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
            service = BooklistService(session)
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

            success = await service.delete_booklist(booklist_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
                )

        return {"message": "书单删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除书单失败"
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
        - **thread_id**: 帖子ID (必填)
        - **comment**: 推荐语 (可选)
        - **display_order**: 排序序号 (可选)
    """
    try:
        user_id = int(current_user["id"])
        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
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

            added_items = await service.add_threads_to_booklist(
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

            deleted_count = await service.remove_threads_from_booklist(
                booklist_id, request.thread_ids
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
    offset: int = Query(default=0, ge=0, description="结果的偏移页，从0开始"),
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """
    分页获取书单内的帖子详情

    - booklist_id: 书单ID
    - limit: 返回数量
    - offset: 偏移页
    """
    try:
        async with AsyncSessionFactory() as session:
            service = BooklistService(session)
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

            item_service = BooklistItemService(session)
            items, total = await item_service.get_booklist_items_with_details(
                booklist_id=booklist_id,
                display_type=booklist.display_type,
                limit=limit,
                offset=offset,
            )

            # 检查收藏状态
            collected_thread_ids = set()
            user_id = int(current_user["id"])
            if user_id and items and collection_cog_instance:
                thread_ids = [item.thread_id for item in items]
                async with (
                    collection_cog_instance.get_collection_service() as collection_service
                ):
                    collected_thread_ids = (
                        await collection_service.get_collected_target_ids(
                            user_id, CollectionType.THREAD, thread_ids
                        )
                    )

            # 更新收藏状态
            for item in items:
                if item.thread_id in collected_thread_ids:
                    item.collected_flag = True

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
            booklist_service = BooklistService(session)
            booklist_item_service = BooklistItemService(session)
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
            item_service = BooklistItemService(session)
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
            return item_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新书单项失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新书单项失败",
        )
