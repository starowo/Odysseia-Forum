from datetime import datetime
from typing import Optional, Union, Any

from pydantic import BaseModel, Field, field_validator


class BooklistItemAddData(BaseModel):
    """书单项添加数据"""

    thread_id: Union[int, str] = Field(
        ...,
        description="Discord Thread ID，支持整数或数字字符串，范围为 1 至 9223372036854775807，每个 ID 应单独提交",
    )
    """Discord Thread ID"""

    comment: Optional[str] = Field(default=None, description="推荐语/备注")
    """推荐语/备注"""

    display_order: Optional[int] = Field(default=None, description="排序权重")
    """排序权重"""

    tournament_participated_at: Optional[datetime] = Field(
        default=None, description="参赛时间（赛事专用）"
    )
    """参赛时间（赛事专用）"""

    @field_validator("thread_id", mode="before")
    @classmethod
    def convert_id_to_int(cls, v: Any) -> Any:
        """校验帖子 ID 范围并将数字字符串转换为整数。"""
        invalid_message = "帖子 ID 必须是有效的正整数。"
        overflow_message = (
            "帖子 ID 超出有效范围，请检查多个 ID 之间是否遗漏逗号，每个 ID 应单独提交。"
        )
        max_id = 9223372036854775807

        # 转换前比较有效数字长度，避免超长字符串触发整数转换异常。
        if isinstance(v, str):
            if not v or not v.isascii() or not v.isdigit():
                raise ValueError(invalid_message)
            digits = v.lstrip("0") or "0"
            max_digits = str(max_id)
            if len(digits) > len(max_digits) or (
                len(digits) == len(max_digits) and digits > max_digits
            ):
                raise ValueError(overflow_message)
            v = int(digits)

        # 排除布尔值和其他类型，确保传给数据库的是范围内的正整数。
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            raise ValueError(invalid_message)
        if v > max_id:
            raise ValueError(overflow_message)
        return v
