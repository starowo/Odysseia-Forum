from typing import Optional

from sqlmodel import BigInteger, Column, Field, SQLModel, UniqueConstraint


class UserUpdatePreference(SQLModel, table=True):
    """用户更新检测偏好模型，存储自动同步/不再提醒状态"""

    __tablename__ = "user_update_preference"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "thread_id", name="uk_user_thread_update_pref"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(BigInteger, index=True, nullable=False),
        description="用户 Discord ID",
    )
    thread_id: int = Field(
        sa_column=Column(BigInteger, index=True, nullable=False),
        description="帖子 Discord Thread ID",
    )
    auto_sync: bool = Field(
        default=False,
        description="是否自动同步更新到索引页（无需再次确认）",
    )
    no_remind: bool = Field(
        default=False,
        description="是否不再提醒该帖子的更新检测",
    )
