from sqlalchemy import BigInteger, CheckConstraint, Column
from sqlmodel import Field, SQLModel


class TagRelation(SQLModel, table=True):
    """保存自定义标签之间的直接包含或互斥关系。"""

    __tablename__ = "tag_relation"

    source_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True),
        description="关系源标签的内部 ID；包含关系中为子标签",
    )
    """关系源标签的内部 ID；包含关系中为子标签"""

    target_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True),
        description="关系目标标签的内部 ID；包含关系中为父标签",
    )
    """关系目标标签的内部 ID；包含关系中为父标签"""

    kind: str = Field(
        primary_key=True,
        description="关系类型：implies 为有向包含，excludes 为对称互斥；互斥关系按较小 ID 在前存储",
    )
    """关系类型：implies 为有向包含，excludes 为对称互斥；互斥关系按较小 ID 在前存储"""

    # 数据库约束类型和自环；包含关系的传递循环由业务层检查。
    __table_args__ = (
        CheckConstraint(
            "kind IN ('implies', 'excludes') AND source_id <> target_id",
            name="ck_tag_relation",
        ),
    )
