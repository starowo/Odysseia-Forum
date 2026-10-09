from pydantic import BaseModel, Field


class UserRole(BaseModel):
    """当前登录用户在主服务器的管理身份。"""

    is_management_member: bool = Field(
        description="是否拥有主服务器配置的管理组身份组；与 BOT 管理员身份独立判断"
    )
    """是否为主服务器管理组成员；BOT 管理员不会自动视为管理组成员"""

    is_bot_admin: bool = Field(
        description="当前 Discord 用户 ID 是否在服务端 bot_admin_user_ids 配置中"
    )
    """是否为配置中的 BOT 管理员；不要求同时拥有管理组身份组"""
