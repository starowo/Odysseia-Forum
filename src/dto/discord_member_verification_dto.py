"""Discord 成员验证结果 DTO。"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(slots=True)
class DiscordMemberVerificationDto:
    """描述一次 Discord 成员查询的最终结果。"""

    outcome: Literal["verified", "not_member", "unavailable"]
    member: Optional[dict] = None
    status_code: Optional[int] = None
    token_alias: Optional[str] = None
    retry_after: Optional[float] = None
    discord_code: Optional[int] = None
