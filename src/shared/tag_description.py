"""各标签写入口共用的纯文本描述校验。"""

from typing import Annotated

from pydantic import BeforeValidator, Field

from shared.tag_error import TagError

MAX_TAG_DESCRIPTION_LENGTH = 2000
"""标签描述清理首尾空白后的最大字符数"""


def normalize_tag_description(value: str) -> str:
    """清理首尾空白，保留文本内部的换行和空格。"""
    if not isinstance(value, str):
        raise TagError("invalid_description", "描述必须为字符串，不能为 null", 422)
    value = value.strip()
    if len(value) > MAX_TAG_DESCRIPTION_LENGTH:
        raise TagError("invalid_description", "描述最多 2000 字", 422)
    return value


def validate_description_input(value):
    """把领域错误转换为请求/导入清单的字段校验错误。"""
    try:
        return normalize_tag_description(value)
    except TagError as exc:
        raise ValueError(str(exc)) from exc


TagDescription = Annotated[
    str,
    BeforeValidator(validate_description_input),
    Field(max_length=MAX_TAG_DESCRIPTION_LENGTH),
]
"""HTTP 请求和导入清单共用的描述字段类型，校验规则与领域服务一致"""
