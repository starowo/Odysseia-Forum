from dataclasses import dataclass, field


@dataclass
class TagCommand:
    """跨模块传递标签命令与可信认证用户 ID。"""

    action: str
    """标签领域操作类型，由事件处理器按白名单分派"""

    actor_id: int
    """已认证操作者的 Discord 用户 ID，不接受请求体指定的身份"""

    payload: dict = field(default_factory=dict)
    """具体操作的参数字典；由 API 或 BOT 入口组装"""
