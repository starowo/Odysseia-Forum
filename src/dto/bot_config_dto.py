"""BotConfig 数据传输对象 — 安全用于进程生命周期缓存。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BotConfigDTO(BaseModel):
    """BotConfig 的轻量 DTO。可安全缓存在进程内存中。"""

    type: int = Field(description="配置类型唯一标识")
    type_str: str = Field(description="配置类型的字符串说明")
    value_int: Optional[int] = Field(default=None, description="整数配置值")
    value_float: Optional[float] = Field(default=None, description="浮点数配置值")
    config_str: str = Field(default="", description="预留的字符串配置字段")
    tips: str = Field(default="", description="该配置的含义或提示")
    update_time: datetime = Field(description="最近更新时间 (UTC)")
    update_user_id: Optional[int] = Field(
        default=None, description="最后修改此配置的用户 ID"
    )

    @staticmethod
    def from_orm(config) -> "BotConfigDTO":
        """从 BotConfig ORM 对象构建 BotConfigDTO（须在 session 内调用）。"""
        return BotConfigDTO(
            type=config.type,
            type_str=config.type_str,
            value_int=config.value_int,
            value_float=config.value_float,
            config_str=config.config_str,
            tips=config.tips,
            update_time=config.update_time,
            update_user_id=config.update_user_id,
        )
