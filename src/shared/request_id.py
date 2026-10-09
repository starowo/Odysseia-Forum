import re
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field


def parse_request_id(value: object) -> int:
    """接受十进制字符串或整数 ID，在接口边界转换为整数。"""
    # 拒绝布尔值和浮点数，避免隐式转换造成错误 ID。
    if type(value) is int:
        return value
    if isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+", value):
        return int(value)
    raise ValueError("ID 必须为十进制字符串或整数")


RequestId = Annotated[
    int, BeforeValidator(parse_request_id, json_schema_input_type=str | int)
]
"""请求允许字符串或整数，校验后的业务值始终为整数。"""


def require_positive_id(value: int) -> int:
    """保留标签管理请求中 ID 必须大于零的限制。"""
    if value <= 0:
        raise ValueError("ID 必须大于零")
    return value


PositiveRequestId = Annotated[
    int,
    BeforeValidator(
        parse_request_id,
        json_schema_input_type=Annotated[str, Field(pattern=r"^\+?0*[1-9][0-9]*$")]
        | Annotated[int, Field(gt=0)],
    ),
    AfterValidator(require_positive_id),
]
"""要求大于零的请求 ID，同时在字符串和整数 Schema 中声明限制。"""
