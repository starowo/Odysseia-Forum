import logging
from collections import defaultdict
from typing import Dict, List

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.tag_service import TagService

logger = logging.getLogger(__name__)


class TagCacheService:
    """
    一个封装了标签缓存的服务
    """

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self._id_to_name: Dict[int, str] = {}
        self._name_to_ids: Dict[str, List[int]] = defaultdict(list)
        self._unique_tag_names: List[str] = []
        self.global_merged_tags: list[str] = []

    async def build_cache(self):
        """
        从数据库加载所有标签，并构建/重建缓存。
        这应该在机器人启动时以及索引更新后调用。
        """
        logger.debug("Building tag cache...")
        async with self.session_factory() as session:
            tag_service = TagService(session)
            all_tags = await tag_service.get_all_tags()
            all_unique_tags_from_indexed_threads = (
                await tag_service.get_all_unique_tags_from_indexed_threads()
            )

        self._id_to_name.clear()
        self._name_to_ids.clear()

        temp_name_to_ids = defaultdict(list)
        for tag in all_tags:
            self._id_to_name[tag.id] = tag.name
            temp_name_to_ids[tag.name].append(tag.id)

        self._name_to_ids = dict(temp_name_to_ids)
        self._unique_tag_names = sorted(self._name_to_ids.keys())
        logger.info(
            f"Tag cache built. Found {len(all_tags)} tags, "
            f"{len(self._unique_tag_names)} unique names."
        )

        self.global_merged_tags = sorted(
            [tag.name for tag in all_unique_tags_from_indexed_threads]
        )
        logger.info(
            f"全局合并标签预计算完成，共 {len(self.global_merged_tags)} 个唯一标签"
        )

    def get_name_by_id(self, tag_id: int) -> str | None:
        """从缓存中通过ID获取标签名称。"""
        return self._id_to_name.get(tag_id)

    def get_ids_by_name(self, tag_name: str) -> List[int]:
        """从缓存中通过名称获取所有对应的标签ID。"""
        return self._name_to_ids.get(tag_name, [])

    def get_all_tag_details(self) -> Dict[str, List[int]]:
        """获取所有标签名称及其对应的ID列表。"""
        return self._name_to_ids

    def get_unique_tag_names(self) -> List[str]:
        """获取所有去重并排序后的标签名称列表。"""
        return self._unique_tag_names

    def get_global_merged_tags(self) -> list[str]:
        """获取预计算的全局合并标签列表。"""
        return self.global_merged_tags
