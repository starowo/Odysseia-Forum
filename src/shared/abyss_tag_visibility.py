from collections.abc import Iterable


def can_view_abyss_tags(role_ids: Iterable[object], abyss_config: dict | None) -> bool:
    """按现有 abyss 身份组配置判断是否展示深渊向 TAG 候选。"""
    required_role_id = str((abyss_config or {}).get("required_role_id") or "")
    roles = {str(role_id) for role_id in role_ids}
    return bool(required_role_id) and required_role_id in roles


def can_discord_user_view_abyss_tags(
    bot: object, user_id: int, main_guild_id: int, abyss_config: dict | None
) -> bool:
    """使用 BOT 的主服务器成员缓存判断深渊向 TAG 候选可见性。"""
    get_guild = getattr(bot, "get_guild", None)
    guild = get_guild(main_guild_id) if callable(get_guild) else None
    member = guild.get_member(user_id) if guild is not None else None
    role_ids = [role.id for role in getattr(member, "roles", [])]
    return can_view_abyss_tags(role_ids, abyss_config)
