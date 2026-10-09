from datetime import datetime

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel


class DiscordTagSyncState(SQLModel, table=True):
    """保存完整频道快照检查点，空列表也推进检查点。"""

    __tablename__ = "discord_tag_sync_state"
    channel_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True),
        description="已成功读取完整标签列表的频道 ID",
    )
    """成功同步的频道 ID"""
    observed_at: datetime = Field(
        description="完整快照开始读取时间（UTC），用于拒绝过期事件"
    )
    """最近一次成功完整快照时间"""
