"""使用多个 Bot Token 验证 Discord 服务器成员。

总体流程：每次请求轮换起始 Token，跳过冷却中的 Token，并在限流、凭证错误、
Discord 服务异常或网络异常时依次切换。只有 Discord 明确返回 Unknown Member
才会认定“不是成员”；其他 Token 全部不可用时统一返回临时故障，交由认证路由
决定是否使用 24 小时内验证过的旧身份组。
"""

import logging
import time
from typing import Optional

import httpx

from dto.discord_member_verification_dto import DiscordMemberVerificationDto

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"
TOKEN_ERROR_COOLDOWN_SECONDS = 300.0
TRANSIENT_ERROR_COOLDOWN_SECONDS = 5.0


class DiscordMemberVerifier:
    """轮询 Bot Token，并在单个 Token 失败时自动切换。"""

    def __init__(self, guild_id: str, primary_token: str, auxiliary_tokens: list[str]):
        """初始化成员验证器并对 Token 去重。"""
        # 主 Token 固定排在首位，辅助 Token 只参与认证请求
        unique_tokens: list[str] = []
        for token in [primary_token, *auxiliary_tokens]:
            stripped = token.strip()
            if stripped and stripped not in unique_tokens:
                unique_tokens.append(stripped)

        if not unique_tokens:
            raise ValueError("身份验证至少需要一个 Bot Token")

        self._guild_id = guild_id
        self._tokens = [
            {
                "alias": "primary" if index == 0 else f"aux-{index}",
                "value": token,
            }
            for index, token in enumerate(unique_tokens)
        ]
        self._next_index = 0
        self._cooldowns: dict[str, float] = {}

    @property
    def token_count(self) -> int:
        """返回 Token 池中的有效 Token 数量。"""
        return len(self._tokens)

    @property
    def token_aliases(self) -> list[str]:
        """返回可安全写入日志的 Token 别名。"""
        return [str(item["alias"]) for item in self._tokens]

    def _ordered_available_tokens(self) -> tuple[list[dict[str, str]], Optional[float]]:
        """按轮询顺序返回当前可用 Token。"""
        # 每个请求向后移动起点，使正常流量均匀落到不同 Token
        now = time.monotonic()
        start_index = self._next_index
        self._next_index = (self._next_index + 1) % len(self._tokens)
        ordered = self._tokens[start_index:] + self._tokens[:start_index]
        available = [
            item
            for item in ordered
            if self._cooldowns.get(str(item["alias"]), 0.0) <= now
        ]

        # 冷却中的 Token 不参与当前请求，避免持续撞击同一个限流桶
        if available:
            return available, None

        remaining = [max(0.0, deadline - now) for deadline in self._cooldowns.values()]
        return [], min(remaining) if remaining else None

    @staticmethod
    def _safe_error_details(response: httpx.Response) -> tuple[Optional[int], str]:
        """读取不会包含凭证的 Discord 错误字段。"""
        try:
            payload = response.json()
        except ValueError:
            return None, "non_json_response"

        code = payload.get("code")
        message = str(payload.get("message", ""))[:200]
        return code if isinstance(code, int) else None, message

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> Optional[float]:
        """从 Discord 响应中解析限流等待时间。"""
        raw_header = response.headers.get("Retry-After")
        if raw_header:
            try:
                return max(0.0, float(raw_header))
            except ValueError:
                pass

        try:
            raw_body = response.json().get("retry_after")
            return max(0.0, float(raw_body)) if raw_body is not None else None
        except (ValueError, TypeError, AttributeError):
            return None

    def _apply_cooldown(
        self, alias: str, status_code: Optional[int], retry_after: Optional[float]
    ) -> None:
        """根据失败类型暂停使用对应 Token。"""
        # 429 尊重 Discord 等待时间，凭证错误比普通网络故障隔离更久
        if status_code == 429:
            cooldown = retry_after or TRANSIENT_ERROR_COOLDOWN_SECONDS
        elif status_code in {401, 403}:
            cooldown = TOKEN_ERROR_COOLDOWN_SECONDS
        else:
            cooldown = TRANSIENT_ERROR_COOLDOWN_SECONDS
        self._cooldowns[alias] = time.monotonic() + cooldown

    async def verify_member(
        self,
        user_id: str,
        attempt_id: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> DiscordMemberVerificationDto:
        """查询指定用户，并在可恢复故障时尝试池中的下一个 Token。"""
        # 先取得本轮查询顺序，池中全部冷却时直接返回可恢复故障
        tokens, pool_retry_after = self._ordered_available_tokens()
        if not tokens:
            logger.error(
                "Discord成员查询失败 attempt_id=%s user_id=%s step=token_pool "
                "status=all_cooling_down retry_after=%.3f",
                attempt_id,
                user_id,
                pool_retry_after or 0.0,
            )
            return DiscordMemberVerificationDto(
                outcome="unavailable", retry_after=pool_retry_after
            )

        owns_client = client is None
        active_client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        )
        last_status: Optional[int] = None
        last_alias: Optional[str] = None
        last_retry_after: Optional[float] = None
        last_discord_code: Optional[int] = None

        try:
            for token_data in tokens:
                alias = str(token_data["alias"])
                last_alias = alias
                # 单个 Token 的网络异常不能直接让用户掉线，继续尝试下一个 Token
                try:
                    response = await active_client.get(
                        f"{DISCORD_API_BASE}/guilds/{self._guild_id}/members/{user_id}",
                        headers={"Authorization": f"Bot {token_data['value']}"},
                    )
                except httpx.RequestError as exc:
                    self._apply_cooldown(alias, None, None)
                    logger.warning(
                        "Discord成员查询异常 attempt_id=%s user_id=%s "
                        "token_alias=%s exception=%s",
                        attempt_id,
                        user_id,
                        alias,
                        type(exc).__name__,
                        exc_info=True,
                    )
                    continue

                last_status = response.status_code
                # 成功响应必须能解析为成员对象，否则仍按临时故障处理
                if response.status_code == 200:
                    try:
                        member = response.json()
                    except ValueError:
                        self._apply_cooldown(alias, response.status_code, None)
                        logger.error(
                            "Discord成员查询失败 attempt_id=%s user_id=%s "
                            "token_alias=%s status=200 error=invalid_json",
                            attempt_id,
                            user_id,
                            alias,
                            exc_info=True,
                        )
                        continue
                    return DiscordMemberVerificationDto(
                        outcome="verified",
                        member=member,
                        status_code=response.status_code,
                        token_alias=alias,
                    )

                discord_code, error_message = self._safe_error_details(response)
                retry_after = self._parse_retry_after(response)
                last_retry_after = retry_after
                last_discord_code = discord_code
                is_unknown_member = (
                    response.status_code == 404 and discord_code == 10007
                )
                log_method = logger.warning if is_unknown_member else logger.error
                log_method(
                    "Discord成员查询失败 attempt_id=%s user_id=%s token_alias=%s "
                    "status=%s discord_code=%s retry_after=%s message=%s",
                    attempt_id,
                    user_id,
                    alias,
                    response.status_code,
                    discord_code,
                    retry_after,
                    error_message,
                )

                # 只有 Discord 的 Unknown Member 才能证明用户不是服务器成员
                if is_unknown_member:
                    return DiscordMemberVerificationDto(
                        outcome="not_member",
                        status_code=response.status_code,
                        token_alias=alias,
                        discord_code=discord_code,
                    )

                # 其余错误均可恢复，暂停当前 Token 后继续故障转移
                self._apply_cooldown(alias, response.status_code, retry_after)
        finally:
            if owns_client:
                await active_client.aclose()

        return DiscordMemberVerificationDto(
            outcome="unavailable",
            status_code=last_status,
            token_alias=last_alias,
            retry_after=last_retry_after,
            discord_code=last_discord_code,
        )
