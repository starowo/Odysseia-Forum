import re

def process_string_to_set(s: str) -> set[str]:
    """使用正则表达式分割字符串，并返回一个干净的、去重的集合"""
    if not s:
        return set()
    return {p.strip() for p in re.split(r"[，,/\s]+", s) if p.strip()}