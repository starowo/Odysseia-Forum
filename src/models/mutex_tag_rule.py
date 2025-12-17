from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models import MutexTagGroup


class MutexTagRule(SQLModel, table=True):
    """
    互斥标签规则的具体条目。
    每个条目包含一个标签名和其在一个组内的优先级。
    """

    __tablename__ = "mutex_tag_rule"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="mutex_tag_group.id")
    tag_name: str = Field(index=True, description="直接存储标签的名称")
    priority: int = Field(default=0, description="优先级，数字越小优先级越高 (0为最高)")

    # 正向关系，用于ORM查询
    group: "MutexTagGroup" = Relationship(back_populates="rules")
