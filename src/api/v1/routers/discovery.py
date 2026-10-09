import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.v1.dependencies.security import get_current_user, require_auth
from api.v1.schemas.discovery import DiscoveryRailsResponse
from api.v1.schemas.search import ThreadDetail
from api.v1.utils import ThreadDetailBuilder
from core.cache_service import CacheService
from core.collection_repository import CollectionRepository
from core.thread_presentation_service import ThreadPresentationService
from core.preferences_repository import PreferencesRepository
from core.thread_repository import ThreadRepository
from discovery.discovery_service import DiscoveryService
from dto.preferences.user_search_preferences_dto import UserSearchPreferencesDTO
from shared.channel_mapping_utils import ChannelMappingUtils
from shared.enum import AbyssDefaults, CollectionType

logger = logging.getLogger(__name__)

async_session_factory: Optional[async_sessionmaker] = None
main_guild_id: int = 0  # 注入的主服务器 ID
channel_mappings_config: Dict[int, List[Dict]] = {}  # 注入的频道映射配置
cache_service_instance: Optional[CacheService] = None  # 注入的缓存服务
abyss_config: Dict[str, Any] = {
    "channel_ids": AbyssDefaults.CHANNEL_IDS,
    "required_role_id": AbyssDefaults.REQUIRED_ROLE_ID,
}
discovery_ignore_channel_ids: List[int] = []

router = APIRouter(
    prefix="/discovery", tags=["发现"], dependencies=[Depends(require_auth)]
)


def _resolve_rails_channel_ids(
    requested_channel_ids: Optional[List[int]],
) -> Optional[List[int]]:
    """解析 rails 请求频道映射，并优先移除广场忽略频道。"""
    if requested_channel_ids is None:
        return None
    if not requested_channel_ids:
        return []
    if not cache_service_instance:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="频道缓存尚未初始化",
        )

    all_indexed_channels = cache_service_instance.get_indexed_channel_ids_list()
    resolution = ChannelMappingUtils(channel_mappings_config).resolve(
        channel_ids=requested_channel_ids,
        include_tags=[],
        exclude_tags=[],
        tag_logic="or",
        all_indexed_channels=all_indexed_channels,
    )
    ignored_channels = set(discovery_ignore_channel_ids)
    return sorted(resolution.searched_ids - ignored_channels)


def _override_preferred_channels(
    prefs: Optional[UserSearchPreferencesDTO],
    requested_channel_ids: Optional[List[int]],
) -> Optional[UserSearchPreferencesDTO]:
    """显式请求频道时仅关闭频道偏好，保留其他用户偏好。"""
    if prefs and requested_channel_ids is not None:
        return prefs.model_copy(update={"preferred_channels": None})
    return prefs


@router.get("/rails", response_model=DiscoveryRailsResponse, summary="获取广场轨道数据")
async def get_discovery_rails(
    limit: int = Query(default=10, ge=1, le=50, description="每条轨道返回的数量"),
    days: int = Query(default=30, ge=1, le=90, description="统计时间跨度(天数)"),
    channel_ids: Optional[List[int]] = Query(
        default=None, description="频道筛选范围，可重复传入多个频道 ID"
    ),
    apply_preferences: bool = Query(
        default=True, description="是否应用当前用户的过滤偏好"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """一次性获取多条轨道数据并处理收藏标记和虚拟标签"""
    if not async_session_factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库尚未初始化"
        )

    user_id = int(current_user["id"]) if current_user and "id" in current_user else None
    prefs = None
    effective_channel_ids = _resolve_rails_channel_ids(channel_ids)

    # 获取用户偏好设置
    if apply_preferences and user_id:
        async with async_session_factory() as session:
            pref_repo = PreferencesRepository(session)
            prefs = await pref_repo.get_user_preferences(user_id, main_guild_id)
            prefs = _override_preferred_channels(prefs, channel_ids)

    try:
        async with async_session_factory() as session:
            service = DiscoveryService(session, discovery_ignore_channel_ids)
            # 获取四条轨道的原始数据
            rails_data = await service.get_discovery_rails(
                limit, days, prefs, effective_channel_ids
            )

            # 汇总所有轨道中出现的帖子 ID 以便批量查询收藏状态
            all_threads = []
            for rail_list in rails_data.values():
                all_threads.extend(rail_list)

            all_ids = [t.thread_id for t in all_threads]
            collected_ids: Set[int] = set()

            # 批量获取当前用户的收藏状态
            if user_id and all_ids:
                coll_repo = CollectionRepository(session)
                collected_ids = await coll_repo.get_collected_target_ids(
                    user_id, CollectionType.THREAD, all_ids
                )

            # 初始化构造器
            builder = ThreadDetailBuilder(channel_mappings_config)
            presentation_context = await ThreadPresentationService(session).load(
                user_id, all_threads
            )

            # 将结果转换为前端 Schema 对象并注入收藏状态与虚拟标签
            return DiscoveryRailsResponse(
                latest=builder.build_list(
                    rails_data["latest"],
                    collected_ids,
                    presentation_context=presentation_context,
                ),
                reaction_surge=builder.build_list(
                    rails_data["reaction_surge"],
                    collected_ids,
                    presentation_context=presentation_context,
                ),
                discussion_surge=builder.build_list(
                    rails_data["discussion_surge"],
                    collected_ids,
                    presentation_context=presentation_context,
                ),
                collection_surge=builder.build_list(
                    rails_data["collection_surge"],
                    collected_ids,
                    presentation_context=presentation_context,
                ),
            )
    except Exception as e:
        logger.error(f"获取广场轨道数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取轨道数据发生异常",
        )


@router.get("/random", response_model=List[ThreadDetail], summary="获取随机帖子")
async def get_random_threads(
    limit: int = Query(default=10, ge=1, le=50, description="抽取数量"),
    channel_ids: Optional[List[int]] = Query(default=None, description="频道筛选范围"),
    exclude_channel_ids: Optional[List[int]] = Query(
        default=None, description="要排除的频道ID列表"
    ),
    include_tags: Optional[List[str]] = Query(default=None, description="包含的标签名"),
    exclude_tags: Optional[List[str]] = Query(
        default=None, description="必须排除的标签名"
    ),
    tag_logic: str = Query(
        default="and",
        description="标签逻辑，'and' 表示必须包含所有标签，'or' 表示包含任意标签",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """根据指定范围随机抽取帖子，包含深渊过滤和虚拟标签解析"""
    # 检查数据库和缓存服务是否就绪
    if not async_session_factory or not cache_service_instance:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="核心服务尚未初始化"
        )

    # 获取当前请求的用户标识和身份组
    user_id = int(current_user["id"]) if current_user and "id" in current_user else None
    user_roles = current_user.get("roles", []) if current_user else []

    # [深渊区权限判断] 读取用户身份组，判断是否需要屏蔽深渊区频道
    final_exclude_channels: list[int] = [
        int(cid) for cid in (exclude_channel_ids or [])
    ]
    if abyss_config:
        required_role = str(abyss_config.get("required_role_id", ""))
        abyss_channels: list[int] = abyss_config.get("channel_ids", [])

        # 若用户未登录，或已登录但身份组列表中不包括深渊区查看需要的身份组
        if not user_roles or required_role not in [str(r) for r in user_roles]:
            final_exclude_channels.extend(abyss_channels)

    # 探索屏蔽频道在随机推荐中始终排除，包括显式选中该频道时。
    final_exclude_channels = list(
        set(final_exclude_channels) | set(discovery_ignore_channel_ids)
    )

    # [处理频道映射虚拟标签] 解析实际搜索的频道ID和标签
    all_indexed_channels = cache_service_instance.get_indexed_channel_ids_list()
    channel_result = ChannelMappingUtils(channel_mappings_config).resolve(
        channel_ids=channel_ids,  # type: ignore
        include_tags=include_tags or [],
        exclude_tags=exclude_tags or [],
        tag_logic=tag_logic,
        all_indexed_channels=all_indexed_channels,
    )
    effective_channel_ids = channel_result.effective_channel_ids
    effective_include_tags = channel_result.effective_include_tags
    effective_exclude_tags = channel_result.effective_exclude_tags
    has_mapping = channel_result.has_mapping

    try:
        async with async_session_factory() as session:
            repo = ThreadRepository(session)

            # 从数据库中获取随机抽取的帖子
            threads = await repo.get_random_threads(
                limit=limit,
                channel_ids=effective_channel_ids,
                exclude_channel_ids=final_exclude_channels,
                include_tags=effective_include_tags,
                exclude_tags=effective_exclude_tags,
                tag_logic=tag_logic,
            )

            # 准备集合用于存放用户已收藏的帖子标识
            collected_ids: Set[int] = set()

            # 若用户已登录且查出结果则批量查询收藏状态
            if user_id and threads:
                thread_ids = [t.thread_id for t in threads]
                coll_repo = CollectionRepository(session)
                collected_ids = await coll_repo.get_collected_target_ids(
                    user_id, CollectionType.THREAD, thread_ids
                )

            builder = ThreadDetailBuilder(channel_mappings_config)
            presentation_context = await ThreadPresentationService(session).load(
                user_id, list(threads)
            )
            channel_to_virtual = None

            # 仅当是在单一频道搜索时，为该上下文计算局部虚拟标签
            if has_mapping and effective_channel_ids and channel_ids:
                origin_ch = int(channel_ids[0]) if channel_ids else None
                if origin_ch:
                    channel_to_virtual = {}
                    for m in channel_mappings_config.get(origin_ch, []):
                        for src_id in m.get("source_channel_ids", []):
                            channel_to_virtual.setdefault(src_id, []).append(
                                m["tag_name"]
                            )

            return builder.build_list(
                threads,
                collected_ids,
                channel_to_virtual=channel_to_virtual,
                presentation_context=presentation_context,
            )

    except Exception as e:
        logger.error(f"获取随机帖子失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取随机帖子发生异常",
        )


@router.get(
    "/rails/{rail_name}",
    response_model=List[ThreadDetail],
    summary="获取单条轨道数据（分页）",
)
async def get_single_rail(
    rail_name: str = Path(
        ...,
        description="轨道名称，可选值: latest / reaction_surge / discussion_surge / collection_surge",
    ),
    limit: int = Query(default=10, ge=1, le=50, description="返回数量"),
    days: int = Query(default=30, ge=1, le=90, description="统计时间跨度(天数)"),
    offset: int = Query(default=0, ge=0, description="偏移量，用于分页"),
    channel_ids: Optional[List[int]] = Query(
        default=None, description="频道筛选范围，可重复传入多个频道 ID"
    ),
    apply_preferences: bool = Query(
        default=True, description="是否应用当前用户的过滤偏好"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取指定单条轨道的数据，支持 offset 分页，用于点击查看更多"""
    valid_rails = {"latest", "reaction_surge", "discussion_surge", "collection_surge"}
    if rail_name not in valid_rails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的轨道名称: {rail_name}，可选值: {', '.join(sorted(valid_rails))}",
        )

    if not async_session_factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库尚未初始化",
        )

    user_id = int(current_user["id"]) if current_user and "id" in current_user else None
    prefs = None
    effective_channel_ids = _resolve_rails_channel_ids(channel_ids)

    # 获取用户偏好设置
    if apply_preferences and user_id:
        async with async_session_factory() as session:
            pref_repo = PreferencesRepository(session)
            prefs = await pref_repo.get_user_preferences(user_id, main_guild_id)
            prefs = _override_preferred_channels(prefs, channel_ids)

    try:
        async with async_session_factory() as session:
            service = DiscoveryService(session, discovery_ignore_channel_ids)
            threads = await service.get_single_rail(
                rail_name=rail_name,
                limit=limit,
                offset=offset,
                days=days,
                prefs=prefs,
                channel_ids=effective_channel_ids,
            )

            # 批量查询收藏状态
            collected_ids: Set[int] = set()
            thread_ids = [t.thread_id for t in threads]
            if user_id and thread_ids:
                coll_repo = CollectionRepository(session)
                collected_ids = await coll_repo.get_collected_target_ids(
                    user_id, CollectionType.THREAD, thread_ids
                )

            builder = ThreadDetailBuilder(channel_mappings_config)
            presentation_context = await ThreadPresentationService(session).load(
                user_id, list(threads)
            )
            return builder.build_list(
                threads,
                collected_ids,
                presentation_context=presentation_context,
            )

    except Exception as e:
        logger.error(f"获取单条轨道数据失败 (rail={rail_name}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取轨道数据发生异常",
        )
