from sqlalchemy import select

from models import DiscordTagSource
from shared.enum.tag_category import TagCategory


async def load_discord_sources(session, tag_ids):
    """批量读取有效来源，避免逐标签查询；失效来源仅供内部审计使用。"""
    if not tag_ids:
        return {}
    rows = (
        await session.execute(
            select(DiscordTagSource)
            .where(
                DiscordTagSource.tag_id.in_(tag_ids),
                DiscordTagSource.deleted_at.is_(None),
            )
            .order_by(DiscordTagSource.channel_id, DiscordTagSource.id)
        )
    ).scalars()
    result = {}
    for source in rows:
        result.setdefault(source.tag_id, []).append(
            {
                "id": str(source.id),
                "discord_tag_id": str(source.discord_tag_id),
                "channel_id": str(source.channel_id)
                if source.channel_id is not None
                else None,
                "name": source.name,
            }
        )
    return result


def tag_data(tag, sources):
    """标准标签对外投影，ID 均使用十进制字符串。"""
    return {
        "id": str(tag.id),
        "name": tag.name,
        "description": tag.description,
        "is_abyss": getattr(tag, "is_abyss", False),
        "source": tag.source,
        "discord_sources": sources.get(tag.id, []),
        "category": tag.category,
        "category_name": TagCategory(tag.category).name if tag.category else None,
        "enabled": tag.enabled,
        "deleted_at": tag.deleted_at,
    }
