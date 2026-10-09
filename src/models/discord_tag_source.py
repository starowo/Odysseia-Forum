from datetime import datetime

from sqlalchemy import BigInteger, Column, Index, text
from sqlmodel import Field, SQLModel


class DiscordTagSource(SQLModel, table=True):
    """记录频道原生标签身份及其当前对应的标准概念，不建立数据库外键。"""

    __tablename__ = "discord_tag_source"
    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        description="来源记录内部 ID",
    )
    """来源记录内部 ID"""
    discord_tag_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, unique=True),
        description="Discord 原生标签 ID，全局唯一",
    )
    """Discord 原生标签 ID"""
    channel_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, index=True),
        description="来源频道 ID；历史数据无法推断时为空",
    )
    """来源频道，待完整同步补齐未知值"""
    tag_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, index=True),
        description="当前标准标签内部 ID",
    )
    """来源当前对应的标准概念"""
    name: str = Field(description="DC 原始名称，按完整名称归一")
    """DC 原始名称"""
    synced_at: datetime | None = Field(
        default=None, description="最近成功确认时间（UTC）"
    )
    """最近成功同步时间"""
    deleted_at: datetime | None = Field(
        default=None, description="来源失效时间（UTC），为空表示有效"
    )
    """来源失效时间，不代表标准概念删除"""
    __table_args__ = (
        Index(
            "uq_discord_source_channel_concept",
            "channel_id",
            "tag_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
