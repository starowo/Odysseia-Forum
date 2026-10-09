import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from api.v1.dependencies.security import require_auth
from dto.author import AuthorProfileResponse, AuthorStats
from core.author_repository import AuthorRepository
from shared.database import AsyncSessionFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/authors", tags=["作者"])


@router.get(
    "/{author_id}", response_model=AuthorProfileResponse, summary="获取作者详情与统计"
)
async def get_author_profile(
    author_id: int, current_user: Dict[str, Any] = Depends(require_auth)
):
    """根据作者ID获取作者信息及统计摘要。"""
    try:
        async with AsyncSessionFactory() as session:
            service = AuthorRepository(session)

            author = await service.get_author(author_id)
            if not author:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="作者不存在"
                )

            stats_dict = await service.get_author_stats(author_id)

            return AuthorProfileResponse(
                id=author.id,
                name=author.name,
                global_name=author.global_name,
                display_name=author.display_name,
                avatar_url=author.avatar_url,
                stats=AuthorStats(**stats_dict),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取作者详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取作者详情失败"
        )
