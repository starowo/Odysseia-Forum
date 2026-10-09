from datetime import datetime
from typing import Optional

from sqlmodel import BigInteger, Column, Field, SQLModel

from shared.time_utils import utc_now


class Author(SQLModel, table=True):
    """存储作者信息"""

    id: int = Field(sa_column=Column(BigInteger, primary_key=True, autoincrement=False))
    name: str = Field(description="用户的唯一用户名")
    global_name: Optional[str] = Field(
        default=None, description="用户在 Discord 上的全局显示名称"
    )
    display_name: str = Field(description="用户的显示名称")
    avatar_url: Optional[str] = Field(default=None, description="用户头像的 URL")

    last_updated: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": utc_now},
        description="此条记录的最后更新时间 (UTC)",
    )
