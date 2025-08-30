import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, delete

from shared.models.mutex_tag_group import MutexTagGroup
from shared.models.mutex_tag_rule import MutexTagRule

logger = logging.getLogger(__name__)

class ConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_mutex_groups_with_rules(self) -> List[MutexTagGroup]:
        """
        获取所有互斥标签组及其关联的规则。
        使用 selectinload 避免 N+1 查询问题。
        """
        result = await self.session.execute(
            select(MutexTagGroup).options(selectinload(MutexTagGroup.rules)) # type: ignore
        )
        return list(result.scalars().unique().all())

    async def add_mutex_group(self, tag_names: List[str]) -> MutexTagGroup:
        """
        添加一个新的互斥标签组及其规则。
        tag_names 列表中的顺序决定了优先级，越靠前优先级越高 (priority 0 最高)。
        """
        new_group = MutexTagGroup()
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