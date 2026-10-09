from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TagStatsRequest(BaseModel):
    """获取标签聚合统计信息的请求体"""

    guild_id: Optional[int] = Field(default=None, description="服务器的 Discord ID")
    """服务器的 Discord ID"""

    channel_ids: Optional[List[int]] = Field(
        default=None, description="指定频道 ID 列表"
    )
    """指定频道 ID 列表"""

    include_virtual: bool = Field(
        default=True, description="是否包含虚拟映射标签的统计"
    )
    """是否包含虚拟映射标签的统计"""

    @field_validator("guild_id", "channel_ids", mode="before")
    @classmethod
    def validate_ids(cls, value):
        """验证并转换 ID 字段，支持字符串形式的数字"""
        if value is None:
            return value

        # 如果是列表，处理列表中的每个元素
        if isinstance(value, list):
            processed = []
            for item in value:
                if isinstance(item, str) and item.isdigit():
                    processed.append(int(item))
                elif isinstance(item, int):
                    processed.append(item)
                else:
                    # 如果不是数字字符串或整数，保持原样，后续验证会失败
                    processed.append(item)
            return processed

        # 如果是字符串数字，转换为整数
        if isinstance(value, str) and value.isdigit():
            return int(value)

        return value
