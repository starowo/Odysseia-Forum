"""频道同步服务 —— 从 Discord API 按需索引频道"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.channel import Channel

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"


class ChannelSyncService:
    """从 Discord REST API 获取频道信息并写入 channel 表"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    async def fetch_and_index(
        self, session: AsyncSession, channel_id: int
    ) -> Optional[Channel]:
        """从 Discord API 获取频道信息并写入 channel 表

        若频道已存在则跳过，保证幂等。
        """
        # 先查本地是否已有
        result = await session.execute(
            select(Channel).where(Channel.channel_id == channel_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # 调 Discord REST API 获取频道信息
        channel_data = await self._fetch_channel(channel_id)
        if channel_data is None:
            return None

        # 构造 Channel 并写入
        channel = Channel(
            channel_id=channel_id,
            guild_id=int(channel_data["guild_id"]),
            name=channel_data["name"],
            topic=channel_data.get("topic"),
            category_id=int(channel_data["parent_id"])
            if channel_data.get("parent_id")
            else None,
            created_at=parse_discord_snowflake(channel_id),
        )

        # ON CONFLICT 幂等处理
        stmt = insert(Channel).values(
            channel_id=channel.channel_id,
            guild_id=channel.guild_id,
            name=channel.name,
            topic=channel.topic,
            category_id=channel.category_id,
            created_at=channel.created_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["channel_id"],
            set_={
                "name": stmt.excluded.name,
                "topic": stmt.excluded.topic,
                "category_id": stmt.excluded.category_id,
            },
        )
        await session.execute(stmt)
        await session.commit()

        # 重新查询返回
        result = await session.execute(
            select(Channel).where(Channel.channel_id == channel_id)
        )
        return result.scalar_one()

    async def _fetch_channel(self, channel_id: int) -> Optional[dict]:
        """调 Discord REST API 获取频道信息"""
        url = f"{DISCORD_API_BASE}/channels/{channel_id}"
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"频道 {channel_id} 不存在或 Bot 无权访问")
                    return None
                else:
                    logger.error(
                        f"获取频道 {channel_id} 失败，HTTP {response.status_code}"
                    )
                    return None
        except Exception:
            logger.error(f"获取频道 {channel_id} 时网络异常", exc_info=True)
            return None


def parse_discord_snowflake(snowflake_id: int) -> datetime:
    """从 Discord snowflake ID 解析创建时间"""
    discord_epoch = 1420070400000
    timestamp_ms = (snowflake_id >> 22) + discord_epoch
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).replace(
        tzinfo=None
    )
