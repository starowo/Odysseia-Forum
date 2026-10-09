import httpx

from core.tag_access_service import TagAccessService
from dto.meta.user_role import UserRole
from shared.tag_error import TagError


class UserRoleService:
    """复用共享权限核验逻辑，独立查询用户的两种管理身份。"""

    def __init__(self, config: dict):
        self.access = TagAccessService(config)
        self.management_role_id = str(config.get("management_role_id") or "")

    async def get_role(self, user_id: int) -> UserRole:
        """读取 BOT 管理员配置和主服务器成员身份组。"""
        is_bot_admin = self.access.bot_admin(user_id)
        is_management_member = False

        # 即使是 BOT 管理员，也独立核验实际管理组身份。
        if self.management_role_id:
            try:
                roles = await self.access.roles(user_id, self.access.main_guild)
                is_management_member = self.management_role_id in roles
            except TagError as exc:
                # 不属于主服务器的用户仍可能是全局 BOT 管理员。
                if exc.status != 403:
                    raise
            except (httpx.RequestError, ValueError) as exc:
                raise TagError(
                    "permission_unavailable", "暂时无法查询用户管理身份", 503
                ) from exc

        return UserRole(
            is_management_member=is_management_member,
            is_bot_admin=is_bot_admin,
        )
