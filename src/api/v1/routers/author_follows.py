import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select

from api.v1.dependencies.security import get_current_user, require_auth
from api.v1.schemas.author_follow import (
    AuthorFollowItem,
    AuthorFollowList,
    AuthorFollowState,
)
from api.v1.schemas.search import AuthorDetail
from core.author_follow_repository import AuthorFollowRepository
from models import Author
from shared.database import AsyncSessionFactory

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/author-follows",
    tags=["作者关注"],
    dependencies=[Depends(require_auth)],
)


@router.post("/{author_id}", response_model=AuthorFollowState, summary="关注作者")
async def follow_author(
    author_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> AuthorFollowState:
    """幂等关注指定作者且不补发历史通知。"""
    user_id = int(current_user["id"])
    if user_id == author_id:
        raise HTTPException(status_code=400, detail="不能关注自己")
    async with AsyncSessionFactory() as session:
        author_exists = (
            await session.execute(select(Author.id).where(Author.id == author_id))
        ).scalar_one_or_none()
        if author_exists is None:
            raise HTTPException(status_code=404, detail="作者不存在")
        relation = await AuthorFollowRepository(session).set_active(
            user_id, author_id, True
        )
        if relation is None:
            raise RuntimeError("关注作者后未取得关系记录")
        # 提交会使 ORM 字段过期，先生成独立响应，避免返回时触发隐式异步查询。
        result = AuthorFollowState(
            author_id=relation.author_id,
            followed_at=relation.followed_at,
            active=relation.active_flag,
        )
        await session.commit()
        return result


@router.delete("/{author_id}", status_code=204, summary="取消关注作者")
async def unfollow_author(
    author_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    """软取消作者关注且保留已有通知。"""
    user_id = int(current_user["id"])
    async with AsyncSessionFactory() as session:
        await AuthorFollowRepository(session).set_active(user_id, author_id, False)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=AuthorFollowList, summary="获取关注作者列表")
async def list_author_follows(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    active: bool | None = Query(default=True),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> AuthorFollowList:
    """按最近关注时间分页返回作者关注关系。"""
    user_id = int(current_user["id"])
    async with AsyncSessionFactory() as session:
        rows, total = await AuthorFollowRepository(session).list_for_user(
            user_id, active, limit, offset
        )
    return AuthorFollowList(
        results=[
            AuthorFollowItem(
                author=AuthorDetail.model_validate(author),
                followed_at=relation.followed_at,
                active=relation.active_flag,
            )
            for relation, author in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
