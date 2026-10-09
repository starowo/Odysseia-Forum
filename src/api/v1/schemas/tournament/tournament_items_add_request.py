from datetime import datetime
from typing import List, Optional, Union, Any

from pydantic import BaseModel, Field, field_validator


class TournamentItemAddData(BaseModel):
    """赛事项添加数据"""

    thread_id: Union[int, str] = Field(..., description="Discord Thread ID")
    """Discord Thread ID"""

    comment: Optional[str] = Field(None, description="推荐语/备注")
    """推荐语/备注"""

    tournament_participated_at: Optional[datetime] = Field(None, description="参赛时间")
    """参赛时间"""

    @field_validator("thread_id", mode="before")
    @classmethod
    def convert_id_to_int(cls, v: Any) -> Any:
        """将字符串形式的数字转换为整数"""
        if v is None:
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v


class TournamentItemsAddRequest(BaseModel):
    """批量添加赛事项请求"""

    items: List[TournamentItemAddData] = Field(..., description="要添加的帖子列表")
    """要添加的帖子列表"""
