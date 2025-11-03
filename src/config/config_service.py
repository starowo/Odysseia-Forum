import logging
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, update
from sqlalchemy.dialects.sqlite import insert

from shared.models.mutex_tag_group import MutexTagGroup
from shared.models.mutex_tag_rule import MutexTagRule
from shared.models.bot_config import BotConfig
from shared.enum.search_config_type import SearchConfigType, SearchConfigDefaults

logger = logging.getLogger(__name__)


class ConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session
        # 缓存字典
        self._cache: Dict[SearchConfigType, BotConfig] = {}

    async def build_or_refresh_cache(self):
        """
        从数据库加载所有配置项来构建或刷新缓存。
        """
        # logger.info("刷新 BotConfig 缓存...")
        result = await self.session.execute(select(BotConfig))
        all_configs = result.scalars().all()

        # 使用 SearchConfigType 枚举作为键，方便类型提示和访问
        self._cache = {SearchConfigType(config.type): config for config in all_configs}
        # logger.info(f"BotConfig 缓存刷新完毕，共加载 {len(self._cache)} 个配置项。")

    async def get_config_from_cache(
        self, config_type: SearchConfigType
    ) -> Optional[BotConfig]:
        """
        从缓存中异步获取配置项。
        如果缓存中不存在，则尝试刷新整个缓存并重新获取。
        """
        config = self._cache.get(config_type)
        if config is None:
            logger.info(f"配置缓存未命中: {config_type.name}. 正在尝试刷新缓存...")
            await self.build_or_refresh_cache()
            config = self._cache.get(config_type)  # 刷新后重试
            if config is None:
                logger.error(
                    f"刷新缓存后仍然找不到配置: {config_type.name}. "
                    f"请检查数据库中是否存在此配置项，或运行一次初始化。"
                )
        return config

    async def get_all_mutex_groups_with_rules(self) -> List[MutexTagGroup]:
        """
        获取所有互斥标签组及其关联的规则。
        使用 selectinload 避免 N+1 查询问题。
        """
        result = await self.session.execute(
            select(MutexTagGroup).options(selectinload(MutexTagGroup.rules))  # type: ignore
        )
        return list(result.scalars().unique().all())

    async def add_mutex_group(
        self, tag_names: List[str], override_tag_name: Optional[str] = None
    ) -> MutexTagGroup:
        """
        添加一个新的互斥标签组及其规则。
        tag_names 列表中的顺序决定了优先级，越靠前优先级越高 (priority 0 最高)。
        """
        new_group = MutexTagGroup(override_tag_name=override_tag_name)
        self.session.add(new_group)
        await self.session.flush()  # 刷新以获取 new_group.id
        assert new_group.id is not None, "新创建的互斥组ID不应为None"

        rules = []
        for i, tag_name in enumerate(tag_names):
            rule = MutexTagRule(group_id=new_group.id, tag_name=tag_name, priority=i)
            rules.append(rule)
        self.session.add_all(rules)
        await self.session.commit()
        await self.session.refresh(new_group)
        return new_group

    async def delete_mutex_group(self, group_id: int) -> bool:
        """
        删除一个互斥标签组及其所有关联规则。
        """
        # 首先删除所有关联的规则
        rules_statement = select(MutexTagRule).where(MutexTagRule.group_id == group_id)
        rules_result = await self.session.execute(rules_statement)
        rules_to_delete = rules_result.scalars().all()

        for rule in rules_to_delete:
            await self.session.delete(rule)

        # 然后删除组本身
        group_statement = select(MutexTagGroup).where(MutexTagGroup.id == group_id)
        group_result = await self.session.execute(group_statement)
        group = group_result.scalar_one_or_none()

        if group:
            await self.session.delete(group)
            await self.session.commit()
            return True
        await self.session.rollback()
        return False

    async def get_search_config(
        self, config_type: SearchConfigType
    ) -> Optional[BotConfig]:
        """根据类型获取一个具体的搜索配置。"""
        result = await self.session.execute(
            select(BotConfig).where(BotConfig.type == config_type)  # type: ignore
        )
        return result.scalar_one_or_none()

    async def update_search_config_float(
        self, config_type: SearchConfigType, new_value: float, user_id: int
    ) -> bool:
        """更新或创建浮点数类型的搜索配置。"""
        return await self.update_search_config(
            config_type, {"value_float": new_value}, user_id
        )

    async def update_search_config(
        self, config_type: SearchConfigType, new_values: dict, user_id: int
    ) -> bool:
        """
        更新数据库中的配置项，返回是否更新成功。
        """
        # 动态构建要更新的值，并加入 update_user_id
        update_data = new_values.copy()
        update_data["update_user_id"] = user_id

        stmt = (
            update(BotConfig)
            .where(BotConfig.type == config_type)  # type: ignore
            .values(**update_data)
        )
        result = await self.session.execute(stmt)

        if result.rowcount == 0:
            logger.warning(
                f"尝试更新类型为 {config_type.name} 的配置失败，数据库中未找到该行。"
            )
            return False

        await self.session.commit()
        return True

    async def get_all_configurable_search_configs(self) -> List[BotConfig]:
        """获取所有可供用户配置的搜索配置项。"""
        result = await self.session.execute(
            select(BotConfig).order_by(BotConfig.type)  # type: ignore
        )
        return list(result.scalars().all())

    async def initialize_search_configs(self):
        """
        幂等地初始化或验证核心搜索配置项是否存在于数据库中
        """

        # 初始化总展示次数 (N)
        stmt_n = (
            insert(BotConfig)
            .values(
                type=SearchConfigType.TOTAL_DISPLAY_COUNT,
                type_str=SearchConfigType.TOTAL_DISPLAY_COUNT.name,
                value_int=0,
                tips="UCB1算法中的全局总展示次数 (N)",
            )
            .on_conflict_do_nothing(index_elements=["type"])
        )
        await self.session.execute(stmt_n)

        # 初始化探索因子 (C)
        stmt_c = (
            insert(BotConfig)
            .values(
                type=SearchConfigType.UCB1_EXPLORATION_FACTOR,
                type_str=SearchConfigType.UCB1_EXPLORATION_FACTOR.name,
                value_float=SearchConfigDefaults.UCB1_EXPLORATION_FACTOR.value,
                tips="UCB1算法的探索因子C，值越大越倾向于探索新内容",
            )
            .on_conflict_do_nothing(index_elements=["type"])
        )
        await self.session.execute(stmt_c)

        # 初始化实力分权重 (W)
        stmt_w = (
            insert(BotConfig)
            .values(
                type=SearchConfigType.STRENGTH_WEIGHT,
                type_str=SearchConfigType.STRENGTH_WEIGHT.name,
                value_float=SearchConfigDefaults.STRENGTH_WEIGHT.value,
                tips="UCB1算法中实力分(x/n)的权重W",
            )
            .on_conflict_do_nothing(index_elements=["type"])
        )
        await self.session.execute(stmt_w)

        # 初始化互斥标签冲突通知配置
        stmt_mutex_notify = (
            insert(BotConfig)
            .values(
                type=SearchConfigType.NOTIFY_ON_MUTEX_CONFLICT,
                type_str=SearchConfigType.NOTIFY_ON_MUTEX_CONFLICT.name,
                value_int=1,  # 默认开启 (0=关闭, 1=开启)
                tips="当检测到帖子应用了互斥TAG时，是否通知管理组 (0=关, 1=开)",
            )
            .on_conflict_do_nothing(index_elements=["type"])
        )
        await self.session.execute(stmt_mutex_notify)

        await self.session.commit()
        logger.info("核心搜索配置已初始化或验证。")
