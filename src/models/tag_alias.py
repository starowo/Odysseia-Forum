from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel


class TagAlias(SQLModel, table=True):
    """保存标准标签的检索别名，允许不同标签共用同一别名。"""

    __tablename__ = "tag_alias"

    tag_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True),
        description="别名所属标准标签的内部 ID，与别名文本组成联合主键",
    )
    """别名所属标准标签的内部 ID，与别名文本组成联合主键"""

    name: str = Field(
        primary_key=True,
        max_length=200,
        description="检索别名文本；同一标签内唯一，不同标签可共用",
    )
    """检索别名文本；同一标签内唯一，不同标签可共用"""
