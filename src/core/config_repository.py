import logging
from typing import List, Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, update

from models import BotConfig, MutexTagGroup, MutexTagRule
from shared.enum import SearchConfigDefaults, SearchConfigType

logger = logging.getLogger(__name__)


class ConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_mutex_groups_with_rules(self) -> List[MutexTagGroup]:
        """
        获取所有互斥标签组及其关联的规则。
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

    async def initialize_search_configs(self, main_guild_id: int):
        """
        幂等地初始化或验证核心搜索配置项是否存在于数据库中。
        """

        config_statements = [
            insert(BotConfig)
            .values(
                type=SearchConfigType.TOTAL_DISPLAY_COUNT,
                type_str=SearchConfigType.TOTAL_DISPLAY_COUNT.name,
                value_int=0,
                tips="UCB1算法中的全局总展示次数 (N)",
            )
            .on_conflict_do_nothing(constraint="bot_config_type_key"),
            insert(BotConfig)
            .values(
                type=SearchConfigType.UCB1_EXPLORATION_FACTOR,
                type_str=SearchConfigType.UCB1_EXPLORATION_FACTOR.name,
                value_float=SearchConfigDefaults.UCB1_EXPLORATION_FACTOR.value,
                tips="UCB1算法的探索因子C，值越大越倾向于探索新内容",
            )
            .on_conflict_do_nothing(constraint="bot_config_type_key"),
            insert(BotConfig)
            .values(
                type=SearchConfigType.STRENGTH_WEIGHT,
                type_str=SearchConfigType.STRENGTH_WEIGHT.name,
                value_float=SearchConfigDefaults.STRENGTH_WEIGHT.value,
                tips="UCB1算法中实力分(x/n)的权重W",
            )
            .on_conflict_do_nothing(constraint="bot_config_type_key"),
            insert(BotConfig)
            .values(
                type=SearchConfigType.NOTIFY_ON_MUTEX_CONFLICT,
                type_str=SearchConfigType.NOTIFY_ON_MUTEX_CONFLICT.name,
                value_int=1,
                tips="当检测到帖子应用了互斥TAG时，是否通知管理组 (0=关, 1=开)",
            )
            .on_conflict_do_nothing(constraint="bot_config_type_key"),
            insert(BotConfig)
            .values(
                type=SearchConfigType.MAIN_GUILD_ID,
                type_str=SearchConfigType.MAIN_GUILD_ID.name,
                value_int=main_guild_id,
                tips="主服务器 ID，用于多服务器搜索时确认主布局",
            )
            .on_conflict_do_nothing(constraint="bot_config_type_key"),
            insert(BotConfig)
            .values(
                type=SearchConfigType.REDDIT_HOT_TIME_DECAY,
                type_str=SearchConfigType.REDDIT_HOT_TIME_DECAY.name,
                value_float=SearchConfigDefaults.REDDIT_HOT_TIME_DECAY.value,
                tips="Reddit Hot 算法的时间衰减常量（秒），越大高反应帖子停留越久",
            )
            .on_conflict_do_nothing(constraint="bot_config_type_key"),
        ]

        for stmt in config_statements:
            await self.session.execute(stmt)

        await self.session.commit()
        logger.info("核心搜索配置已初始化或验证。")
