import asyncio
import logging
from datetime import datetime, timezone

from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.author_repository import AuthorRepository
from shared.discord_utils import DiscordUtils
from shared.redis_client import RedisManager

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class AuthorCog(commands.Cog, name="Author"):
    def __init__(self, bot: "MyBot", session_factory: async_sessionmaker):
        self.bot = bot
        self.session_factory = session_factory
        self.fetch_authors_task.start()

    def cog_unload(self):
        self.fetch_authors_task.cancel()

    # 定时任务
    @tasks.loop(minutes=10)
    async def fetch_authors_task(self):
        """每隔 10 分钟运行一次，从 Redis 获取排队需要拉取的用户信息"""
        try:
            user_ids = await self._pop_user_ids()
            while user_ids:
                for user_id in user_ids:
                    await self._fetch_and_store_user(user_id)
                    await asyncio.sleep(1.5)
                user_ids = await self._pop_user_ids()
        except Exception as e:
            logger.error(f"执行 fetch_authors_task 时发生异常: {e}", exc_info=True)

    @fetch_authors_task.before_loop
    async def before_fetch_authors_task(self):
        await self.bot.wait_until_ready()

    # -------------------------
    # 缓存失效事件监听
    # -------------------------

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """角色变更时删除认证缓存，让下一次请求实时复验。"""
        if before.roles == after.roles:
            return

        try:
            await RedisManager.get_client().delete(f"user:discord:{after.id}")
        except Exception:
            logger.warning("身份组变化后删除成员缓存失败", exc_info=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """成员离开时删除缓存"""
        try:
            await RedisManager.get_client().delete(f"user:discord:{member.id}")
        except Exception:
            logger.warning("删除成员缓存失败", exc_info=True)

    # -------------------------
    # 辅助方法
    # -------------------------

    @staticmethod
    async def _pop_user_ids() -> list[int]:
        """从 Redis 集合中原子弹出最多 50 个待拉取用户 ID"""
        client = RedisManager.get_client()
        raw_ids = await client.spop("author_fetch_queue", 50)
        if not raw_ids:
            return []
        result: list[int] = []
        for raw in raw_ids:
            text = raw if isinstance(raw, str) else raw.decode("utf-8")
            if text.isdigit():
                result.append(int(text))
        return result

    async def _fetch_and_store_user(self, user_id: int) -> None:
        """拉取单个用户信息并入库；拉取失败时标记已尝试"""
        try:
            user_obj = await DiscordUtils.get_or_fetch_user(
                bot=self.bot, user_id=user_id, guild=None
            )
        except Exception:
            logger.error(f"拉取用户 {user_id} 时发生错误", exc_info=True)
            return

        async with self.session_factory() as session:
            repo = AuthorRepository(session)
            if user_obj:
                await repo.upsert_author(_build_author_data(user_obj))
                logger.debug(f"已成功拉取并更新用户 {user_id} 的信息")
            else:
                await self._touch_author_if_exists(repo, session, user_id)

    async def _touch_author_if_exists(
        self, repo: AuthorRepository, session, user_id: int
    ) -> None:
        """若用户在库则更新 last_updated，若不在库则写入占位数据，避免过期标记导致反复无效拉取"""
        author = await repo.get_author(user_id)
        if not author:
            dummy_author = {
                "id": user_id,
                "name": f"未知用户{user_id}",
                "global_name": None,
                "display_name": f"未知用户{user_id}",
                "avatar_url": None,
                "last_updated": datetime.now(timezone.utc).replace(tzinfo=None),
            }
            await repo.upsert_author(dummy_author)
            logger.debug(f"用户 {user_id} 无法获取且不在库，已写入占位数据")
            return
        author.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(author)
        await session.commit()
        logger.debug(f"拉取用户 {user_id} 失败，已更新 last_updated 时间以免重复拉取")


def _build_author_data(user_obj) -> dict:
    return {
        "id": user_obj.id,
        "name": user_obj.name,
        "global_name": user_obj.global_name,
        "display_name": user_obj.display_name,
        "avatar_url": user_obj.display_avatar.url if user_obj.display_avatar else None,
        "last_updated": datetime.now(timezone.utc).replace(tzinfo=None),
    }


async def setup(bot):
    pass
