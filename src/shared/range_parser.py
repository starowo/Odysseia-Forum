import re
from typing import Tuple

from shared.exceptions import InvalidRangeFormat


def parse_range_string(range_str: str) -> Tuple[int, int, str, str]:
    """
    解析数学区间表示法字符串，如 "[0, 100)" 或 " (50, 200] "
    如果格式或逻辑错误，则抛出 InvalidRangeFormat 异常
    返回一个元组 (min_val, max_val, min_op, max_op)
    min_op/max_op 分别是 '>=' or '>' 和 '<=' or '<'

    """
    range_str = range_str.strip()

    replacements = {"，": ",", "（": "(", "）": ")", "【": "[", "】": "]"}
    for full, half in replacements.items():
        range_str = range_str.replace(full, half)

    # 正则表达式匹配 [ 或 (, 数字, 逗号, 数字, ] 或 )
    match = re.fullmatch(r"([(\[])\s*(-?\d+)\s*,\s*(-?\d+)\s*([)\]])", range_str)

    if not match:
        raise InvalidRangeFormat(
            "格式错误。请使用如 `[10, 100)` 或 `(50, 200]` 的格式。"
        )

    left_bracket, min_str, max_str, right_bracket = match.groups()

    min_val, max_val = int(min_str), int(max_str)

    if min_val > max_val:
        raise InvalidRangeFormat(
            f"逻辑错误：范围的起始值 {min_val} 不能大于结束值 {max_val}"
        )

    min_op = ">=" if left_bracket == "[" else ">"
    max_op = "<=" if right_bracket == "]" else "<"

    return min_val, max_val, min_op, max_op
