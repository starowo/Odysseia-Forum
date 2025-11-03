import discord
import datetime
import logging
import re
import asyncio
from typing import Coroutine, Optional, Union, TYPE_CHECKING, List
from sqlalchemy.ext.asyncio import async_sessionmaker

from ThreadManager.thread_manager_service import ThreadManagerService

if TYPE_CHECKING:
    from bot_main import MyBot
    from .author_service import AuthorService

logger = logging.getLogger(__name__)


class SyncService:
    """
    负责将 Discord 帖子数据同步到数据库的服务
    """

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        author_service: "AuthorService",
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.author_service = author_service

    @staticmethod
    async def _fetch_message_wrapper(fetch_coro: Coroutine) -> discord.Message | None:
        """
        包装一个获取消息的协程
        如果协程成功，返回消息对象；如果抛出 NotFound，返回 None。
        """
        try:
            return await fetch_coro
        except discord.NotFound:
            return None

    async def _parse_thread_data(self, thread: discord.Thread) -> Optional[dict]:
        """
        解析一个帖子，根据其结构（普通或重建）返回标准化的数据字典。
        如果帖子无效或不满足索引条件，返回 None。
        """
        messages = [msg async for msg in thread.history(limit=2, oldest_first=True)]
        if not messages:
            return None

        first_msg = messages[0]
        second_msg = messages[1] if len(messages) > 1 else None

        # 默认值
        final_author_id = thread.owner_id or 0
        final_created_at = thread.created_at
        source_user_for_author_service = thread.owner
        excerpt = ""
        thumbnail_urls: List[str] = []

        reaction_count = (
            max([r.count for r in first_msg.reactions]) if first_msg.reactions else 0
        )

        first_msg_content = first_msg.content or ""

        image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")

        def _is_image_attachment(attachment: discord.Attachment) -> bool:
            content_type = (getattr(attachment, "content_type", None) or "").lower()
            filename = (attachment.filename or "").lower()
            return content_type.startswith("image/") or filename.endswith(
                image_extensions
            )

        def _collect_attachment_urls(message: Optional[discord.Message]) -> List[str]:
            if not message:
                return []
            result = [
                att.url for att in message.attachments if _is_image_attachment(att)
            ]
            for embed in message.embeds:
                if embed.type != "image":
                    continue
                if embed.thumbnail.proxy_url:
                    result.append(embed.thumbnail.proxy_url)
                elif embed.thumbnail.url:
                    result.append(embed.thumbnail.url)
                elif embed.image.proxy_url:
                    result.append(embed.image.proxy_url)
                elif embed.image.url:
                    result.append(embed.image.url)
            return result

        # --- 检查是否为重建帖 ---
        match_id = re.search(r"发帖人[:：\s*]*<@(\d+)>", first_msg_content)
        match_time = re.search(
            r"原始创建时间[:：\s*]*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日.*?(\d{2}):(\d{2})",
            first_msg_content,
        )

        if match_id:
            # --- 是重建帖，执行解析和检查 ---

            # 1. 解析作者和时间
            try:
                final_author_id = int(match_id.group(1))
                if match_time:
                    year, month, day, hour, minute = map(int, match_time.groups())
                    # 假设原始时间是 UTC+8 时区
                    local_tz = datetime.timezone(datetime.timedelta(hours=8))
                    local_dt = datetime.datetime(
                        year, month, day, hour, minute, tzinfo=local_tz
                    )
                    final_created_at = local_dt.astimezone(datetime.timezone.utc)
            except Exception as e:
                logger.warning(
                    f"重建帖 {thread.id} 解析作者或时间失败: {e}。中止对其的索引"
                )
                return None

            # 2. 检查并解析补档链接: https://discord.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID
            match_url = re.search(
                r"补档[:：\s*]*\d+\.\s*\[.*?\]\((https://discord.com/channels/(\d+)/(\d+)/(\d+))\)",
                first_msg_content,
            )
            if not match_url:
                logger.debug(
                    f"重建帖 {thread.id} 的补档图片链接提取失败。中止对其的索引"
                )
                return None

            # 3. 通过API获取补档消息的附件
            try:
                guild_id, channel_id, message_id = map(int, match_url.groups()[1:])
                target_channel = self.bot.get_channel(
                    channel_id
                ) or await self.bot.fetch_channel(channel_id)
                if not isinstance(target_channel, discord.abc.Messageable):
                    logger.warning(
                        f"重建帖 {thread.id} 的补档链接指向了一个非消息频道 (ID: {channel_id})。中止对其的索引"
                    )
                    return None

                # 使用调度器提交API请求
                target_message = await self.bot.api_scheduler.submit(
                    coro_factory=lambda: target_channel.fetch_message(message_id),
                    priority=5,  # 中等优先级
                )

                if not target_message or not target_message.attachments:
                    logger.debug(
                        f"重建帖 {thread.id} 的补档消息 ({message_id}) 不存在或没有附件。中止对其的索引"
                    )
                    return None

                attachment_urls = _collect_attachment_urls(target_message)
                if not attachment_urls:
                    logger.debug(
                        f"重建帖 {thread.id} 的补档消息 ({message_id}) 没有图片附件。中止对其的索引"
                    )
                    return None

                thumbnail_urls.extend(attachment_urls)

            except (discord.NotFound, discord.Forbidden, Exception) as e:
                logger.error(
                    f"重建帖 {thread.id} 获取补档消息时出错: {e}。中止对其的索引",
                    exc_info=True,
                )
                return None

            # 4. 从第二楼获取内容摘要
            if second_msg:
                excerpt_ori = second_msg.content
                potential_reaction_numbers = []

                # 使用正则表达式查找所有“表情符号 + 空格 + 数字”的模式
                emoji_pattern = r"(?:<:\w+:\d+>|[\U00002600-\U000027BF\U0001F000-\U0001FFFF\U0001F900-\U0001F9FF])"
                matches = re.findall(
                    f"{emoji_pattern}\\s*(\\d+)(?=\\s|\\||$)", second_msg.content
                )

                for num_str in matches:
                    try:
                        potential_reaction_numbers.append(int(num_str))
                    except ValueError:
                        logger.warning(
                            f"无法将重建帖 {thread.id} 中的反应数 '{num_str}' 转换为整数",
                            exc_info=True,
                        )

                if potential_reaction_numbers:
                    reaction_count_ori = max(potential_reaction_numbers)
                    reaction_count += reaction_count_ori

                # 从摘要中删除元数据行
                reaction_line_pattern = f"^-#\\s*{emoji_pattern}\\s*\\d+.*$"
                attachment_line_pattern = r"^-#\s*📎\s+.*?\s*\(.*?\)$"
                edited_line_pattern = r"^-#\s*\(已编辑\)$"

                cleaning_pattern = re.compile(
                    f"(?:{reaction_line_pattern}|{attachment_line_pattern}|{edited_line_pattern})\\n?",
                    re.MULTILINE,
                )

                cleaned_excerpt = cleaning_pattern.sub("", excerpt_ori).strip()
                excerpt = cleaned_excerpt

        else:
            # --- 是普通帖 ---
            excerpt = first_msg.content
            attachment_urls = _collect_attachment_urls(first_msg)
            if attachment_urls:
                thumbnail_urls.extend(attachment_urls)
            else:
                # 如果没有附件，则尝试从首楼内容中提取所有图片 URL
                inline_image_urls = re.findall(
                    r"https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)",
                    first_msg.content or "",
                    re.IGNORECASE,
                )
                if inline_image_urls:
                    thumbnail_urls.extend(inline_image_urls)

        if final_author_id and thread.guild:
            asyncio.create_task(
                self.author_service.get_or_fetch_author(
                    author_id=final_author_id,
                    guild=thread.guild,
                    source_member=source_user_for_author_service,
                )
            )

        return {
            "thread_id": thread.id,
            "channel_id": thread.parent_id,
            "title": thread.name,
            "author_id": final_author_id,
            "created_at": final_created_at,
            "last_active_at": discord.utils.snowflake_time(thread.last_message_id)
            if thread.last_message_id
            else thread.created_at,
            "reaction_count": reaction_count,
            "reply_count": thread.message_count,
            "not_found_count": 0,
            "first_message_excerpt": excerpt,
            "thumbnail_urls": thumbnail_urls,
        }

    async def sync_thread(
        self,
        thread: Union[discord.Thread, int],
        priority: int = 10,
        *,
        fetch_if_incomplete: bool = False,
    ):
        """
        同步一个帖子的数据到数据库，包括其标签。
        该方法可以接受一个完整的帖子对象，或者一个帖子ID。
        """
        if isinstance(thread, int):
            thread_id = thread
            try:
                fetched_channel = await self.bot.api_scheduler.submit(
                    coro_factory=lambda tid=thread_id: self.bot.fetch_channel(tid),
                    priority=priority,
                )
                if not isinstance(fetched_channel, discord.Thread):
                    logger.warning(
                        f"sync_thread: 获取到的 channel {thread_id} 不是一个帖子，将标记为未找到。"
                    )
                    async with self.session_factory() as session:
                        repo = ThreadManagerService(session=session)
                        await repo.increment_not_found_count(thread_id=thread_id)
                    return
                thread = fetched_channel
            except discord.NotFound:
                logger.warning(
                    f"sync_thread: 无法找到帖子 {thread_id}，可能已被删除。将增加其 not_found_count。"
                )
                async with self.session_factory() as session:
                    repo = ThreadManagerService(session=session)
                    await repo.increment_not_found_count(thread_id=thread_id)
                return
            except Exception as e:
                logger.error(
                    f"sync_thread: 通过ID {thread_id} 获取帖子时发生未知错误: {e}",
                    exc_info=True,
                )
                return

        elif fetch_if_incomplete:
            try:
                thread_id = thread.id
                thread = await self.bot.api_scheduler.submit(
                    coro_factory=lambda tid=thread_id: self.bot.fetch_channel(tid),
                    priority=priority,
                )
            except discord.NotFound:
                logger.warning(
                    f"sync_thread (fetch_if_incomplete): 无法找到帖子 {thread.id}，可能已被删除。将增加其 not_found_count。"
                )
                async with self.session_factory() as session:
                    repo = ThreadManagerService(session=session)
                    await repo.increment_not_found_count(thread_id=thread.id)
                return

        assert isinstance(thread, discord.Thread)

        # 调用辅助方法解析帖子数据
        thread_data = await self._parse_thread_data(thread)

        # 检查解析结果，如果为 None 则中止同步
        if thread_data is None:
            # logger.info(f"帖子 {thread.id} 不满足索引条件或无效，同步中止。")
            return

        # 准备标签数据并存入数据库
        tags_data = {t.id: t.name for t in thread.applied_tags or []}

        # 先保存帖子数据
        async with self.session_factory() as session:
            repo = ThreadManagerService(session=session)
            await repo.add_or_update_thread_with_tags(
                thread_data=thread_data, tags_data=tags_data
            )

        # 检查是否是首次被关注（检查关注表而不是帖子表）
        is_first_follow = False
        async with self.session_factory() as session:
            from sqlmodel import select, func
            from shared.models.thread_follow import ThreadFollow

            # 检查该帖子是否有任何关注记录
            statement = (
                select(func.count())
                .select_from(ThreadFollow)
                .where(ThreadFollow.thread_id == thread.id)
            )
            result = await session.execute(statement)
            follow_count = result.scalar() or 0
            is_first_follow = follow_count == 0

        # 如果是首次被关注的老帖子，批量添加所有成员到关注列表
        if is_first_follow:
            await self._auto_follow_on_first_detect(thread)

    async def _auto_follow_on_first_detect(self, thread: discord.Thread):
        """首次检测到老帖子时，自动为所有成员添加关注"""
        try:
            # 获取帖子中的所有成员ID
            member_ids = []

            # fetch_members()返回AsyncIterator，直接迭代
            members_iterator = await thread.fetch_members()
            for member in members_iterator:
                # 不用检测机器人，fetch member太慢了
                member_ids.append(member.id)

            if member_ids:
                from ThreadManager.services.follow_service import FollowService

                async with self.session_factory() as session:
                    follow_service = FollowService(session)
                    added_count = await follow_service.batch_add_follows(
                        thread_id=thread.id, user_ids=member_ids
                    )
                    if added_count > 0:
                        logger.info(
                            f"老帖子 {thread.id} 首次检测，为 {added_count} 个成员添加了自动关注"
                        )
        except discord.NotFound:
            logger.warning(f"老帖子 {thread.id} 已被删除，跳过自动关注")
        except discord.Forbidden:
            logger.warning(f"老帖子 {thread.id} 没有权限获取成员列表，跳过自动关注")
        except Exception as e:
            logger.error(f"老帖子自动关注失败 (帖子 {thread.id}): {e}", exc_info=True)
