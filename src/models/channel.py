"""频道模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class Channel(SQLModel, table=True):
    """频道模型（文字频道、后续可扩展论坛频道等）。"""

    __tablename__ = "channel"

    id: Optional[int] = Field(default=None, primary_key=True)
    """数据库主键 ID"""

    channel_id: int = Field(
        sa_column=Column(BigInteger, unique=True, index=True, nullable=False),
        description="Discord 频道 ID",
    )
    """Discord 频道 ID"""

    guild_id: int = Field(
        sa_column=Column(BigInteger, index=True, nullable=False),
        description="所属 Discord 服务器 ID",
    )
    """所属 Discord 服务器 ID"""

    name: str = Field(description="频道名称")
    """频道名称"""

    topic: Optional[str] = Field(default=None, description="频道简介/描述")
    """频道简介/描述"""

    category_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True),
        description="所属频道分组 ID",
    )
    """所属频道分组 ID"""

    created_at: datetime = Field(
        default_factory=utc_now, description="频道在 Discord 中的创建时间"
    )
    """频道在 Discord 中的创建时间"""
