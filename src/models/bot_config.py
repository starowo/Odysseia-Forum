from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.types import Float
from sqlmodel import BigInteger, Column, Field, SQLModel


class BotConfig(SQLModel, table=True):
    """存储机器人全局配置，如 UCB1 参数和统计数据"""

    __tablename__ = "bot_config"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    type: int = Field(unique=True, description="配置类型唯一标识")
    type_str: str = Field(description="配置类型的字符串说明")

    # 使用两个独立的、可为空的字段来存储不同类型的值
    value_int: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger), description="用于存储整数配置值"
    )
    value_float: Optional[float] = Field(
        default=None, sa_column=Column(Float), description="用于存储浮点数配置值"
    )

    config_str: str = Field(default="", description="预留的字符串配置字段")
    tips: str = Field(default="", description="该配置的含义或提示")

    update_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        description="最近更新时间 (UTC)",
    )
    update_user_id: Optional[int] = Field(
        default=None, description="最后修改此配置的用户ID"
    )
