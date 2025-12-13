from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models import MutexTagRule


class MutexTagGroup(SQLModel, table=True):
    """
    互斥标签组的模型。
    一个组本身只是一个容器，具体的规则在 MutexTagRule 中定义。
    """

    __tablename__ = "mutex_tag_group"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)

    override_tag_name: Optional[str] = Field(
        default=None, index=True, description="用于覆盖默认优先级逻辑的标签名"
    )

    # 反向关系，用于ORM查询，方便地获取一个组下的所有规则
    rules: List["MutexTagRule"] = Relationship(back_populates="group")
