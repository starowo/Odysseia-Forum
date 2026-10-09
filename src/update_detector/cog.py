import logging
import os
import re
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.thread_repository import ThreadRepository
from core.thread_update_service import ThreadUpdateError, ThreadUpdateService
from core.user_update_preference_repository import UserUpdatePreferenceRepository
from dto.thread_dto import ThreadDTO
from dto.thread_update_dto import ThreadUpdateDTO
from shared.redis_client import RedisManager
from shared.safe_defer import safe_defer
from update_detector.deepseek_service import DeepSeekService
from update_detector.prompt_builder import build_update_detection_prompt
from update_detector.token_estimator import TokenEstimator
from update_detector.token_stats_service import TokenStatsService
from update_detector.auto_publish_overview_view import (
    AutoPublishOverviewView,
    build_overview_embed,
)
from update_detector.update_detector_views import UpdateDetectorView, build_update_embed

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class UpdateDetector(commands.Cog):
    """监听已索引帖子中的消息，检测发布更新并提醒用户同步"""

    VALID_MODES = {"disabled", "observe", "active"}
    MESSAGE_LINK_PATTERN = re.compile(
        r"^https://(?:www\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)$"
    )

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.cache_service = bot.cache_service
        self.thread_update_service = ThreadUpdateService(session_factory)

        ud_config = config.get("update_detector", {})
        configured_mode = ud_config.get("mode", "disabled")
        if (
            not isinstance(configured_mode, str)
            or configured_mode not in self.VALID_MODES
        ):
            logger.warning(
                "更新检测 mode 非法，已按 disabled 处理: mode=%r",
                configured_mode,
            )
            configured_mode = "disabled"
        self.mode = configured_mode
        self.prompt_message = ud_config.get(
            "prompt_message", "检测到您可能发布了作品的新版本，是否将其同步到索引页？"
        )
        self.min_text_length = ud_config.get("min_text_length", 100)
        self.min_text_length_with_attachment = ud_config.get(
            "min_text_length_with_attachment", 30
        )
        self.deepseek_model = ud_config.get("deepseek_model", "deepseek-v4-flash")
        self.thinking_enabled = ud_config.get("thinking_enabled", True)
        self.max_output_tokens = ud_config.get("max_output_tokens", 2048)
        self.token_estimator = TokenEstimator()
        self.token_stats_service: TokenStatsService | None = None
        if self.mode != "disabled":
            self.token_stats_service = TokenStatsService(RedisManager.get_client())

        self.deepseek_service: DeepSeekService | None = None
        deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if self.mode == "active" and deepseek_api_key:
            self.deepseek_service = DeepSeekService(
                api_key=deepseek_api_key,
                base_url=ud_config.get("deepseek_base_url", "https://api.deepseek.com"),
                model=self.deepseek_model,
                thinking_enabled=self.thinking_enabled,
                max_output_tokens=self.max_output_tokens,
                timeout_seconds=ud_config.get("request_timeout_seconds", 60),
            )
        elif self.mode == "active":
            logger.error("更新检测 active 模式缺少 DEEPSEEK_API_KEY，AI 调用已停用")

        logger.info("UpdateDetector 已加载 (mode=%s)", self.mode)

    async def cog_load(self) -> None:
        """注册跨 Bot 重启仍可响应的静态视图。"""
        self.bot.add_view(UpdateDetectorView(cog=self))
        self.bot.add_view(AutoPublishOverviewView(cog=self))

    async def cog_unload(self):
        if self.deepseek_service:
            await self.deepseek_service.close()

    def _is_channel_indexed(self, channel_id: int) -> bool:
        return self.cache_service.is_channel_indexed(channel_id)

    def _is_potential_update(self, message: discord.Message) -> bool:
        """
        初步筛选：判断消息是否可能是发布更新。
        条件：
        1. 大量文字（>=min_text_length）
        2. 中量文字 + png 图片附件
        3. 中量文字 + json 文件附件
        """
        text_len = len(message.content)
        has_png = any(
            att.filename.lower().endswith(".png") for att in message.attachments
        )
        has_json = any(
            att.filename.lower().endswith(".json") for att in message.attachments
        )
        has_relevant_attachment = has_png or has_json

        if has_relevant_attachment:
            return text_len >= self.min_text_length_with_attachment
        return text_len >= self.min_text_length

    @staticmethod
    def _is_thread_too_new(thread: discord.Thread) -> bool:
        """判断帖子是否仍处于发布后的首个自然 24 小时。"""
        created_at = getattr(thread, "created_at", None)
        return bool(
            created_at and discord.utils.utcnow() - created_at < timedelta(days=1)
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.mode == "disabled":
            return

        if (
            not message.guild
            or not isinstance(message.channel, discord.Thread)
            or message.author.bot
        ):
            return

        thread = message.channel

        # 新帖首日可能仍在用回复补充首楼内容，不进入任何更新检测流程。
        if self._is_thread_too_new(thread):
            return
        if self.mode == "active" and not self.deepseek_service:
            return

        # 只处理已索引频道中的帖子
        if not self._is_channel_indexed(thread.parent_id):
            return

        # 只处理帖子作者发送的消息（非首楼）
        if thread.owner_id != message.author.id:
            return
        if thread.id == message.id:
            return

        if not self._is_potential_update(message):
            return

        # 检查用户偏好
        thread_dto: ThreadDTO | None = None
        async with self.session_factory() as session:
            pref_repository = UserUpdatePreferenceRepository(session)
            pref = await pref_repository.get_preference(message.author.id, thread.id)
            thread_record = await ThreadRepository(session).get_thread_with_tags(
                thread_id=thread.id
            )
            if thread_record:
                thread_dto = ThreadDTO.from_orm(thread_record)

        if pref and pref.no_remind:
            return

        # 构造本地估算和正式调用共用的判断内容
        attachment_filenames = None
        json_filenames = [
            att.filename
            for att in message.attachments
            if att.filename.lower().endswith(".json")
        ]
        if json_filenames:
            attachment_filenames = json_filenames

        # 数据库记录缺失时降级使用 Discord 帖子标题和空首楼。
        thread_title = thread.name
        first_message_content = ""
        if thread_dto:
            thread_title = thread_dto.title
            first_message_content = thread_dto.first_message_excerpt or ""

        system_content, user_content = build_update_detection_prompt(
            thread_title=thread_title,
            first_message_content=first_message_content,
            message_content=message.content,
            attachment_filenames=attachment_filenames,
        )
        if self.mode == "observe":
            estimate = self.token_estimator.estimate(
                system_content=system_content,
                user_content=user_content,
                max_output_tokens=self.max_output_tokens,
            )
            if self.token_stats_service:
                await self.token_stats_service.record_estimate(
                    model=self.deepseek_model,
                    thinking_enabled=self.thinking_enabled,
                    max_output_tokens=self.max_output_tokens,
                    estimate=estimate,
                )
            return

        # 将可选客户端收窄为可调用的服务实例。
        deepseek_service = self.deepseek_service
        if deepseek_service is None:
            return

        result = await deepseek_service.detect_update(
            system_content=system_content,
            user_content=user_content,
        )
        if self.token_stats_service:
            await self.token_stats_service.record_actual(
                model=self.deepseek_model,
                thinking_enabled=self.thinking_enabled,
                max_output_tokens=self.max_output_tokens,
                result=result,
            )
        if not result.is_update:
            return

        message_link = message.jump_url

        # 如果用户设置了自动同步，直接执行同步
        if pref and pref.auto_sync:
            try:
                update = await self._publish_message(
                    thread,
                    message,
                    "系统自动同步",
                    None,
                )
                await self._send_auto_overview(message, update)
                logger.info("帖子 %s 自动同步更新: %s", thread.id, message_link)
            except Exception:
                logger.exception("帖子 %s 自动同步更新失败", thread.id)
            return

        # 发送提醒 embed
        embed = build_update_embed(self.prompt_message)
        view = UpdateDetectorView(
            cog=self,
            thread_id=thread.id,
            author_id=message.author.id,
            message_link=message_link,
        )

        try:
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: message.reply(embed=embed, view=view),
                priority=5,
            )
        except Exception:
            logger.error(f"发送更新检测提醒失败 (帖子 {thread.id})", exc_info=True)

    async def do_sync_update(self, thread_id: int, message_link: str) -> bool:
        """兼容旧调用方，以默认描述发布更新。"""
        try:
            thread = self.bot.get_channel(thread_id)
            if not isinstance(thread, discord.Thread):
                thread = await self.bot.fetch_channel(thread_id)
            if not isinstance(thread, discord.Thread):
                return False
            match = self.MESSAGE_LINK_PATTERN.fullmatch(message_link.strip())
            if match is None or int(match.group(2)) != thread_id:
                return False
            message_id = int(match.group(3))
            message = await thread.fetch_message(message_id)
            await self._publish_message(
                thread,
                message,
                "系统自动同步",
                None,
            )
            return True
        except Exception:
            logger.exception("兼容更新发布失败: thread_id=%s", thread_id)
            return False

    @staticmethod
    def build_message_link(guild_id: int, thread_id: int, message_id: int) -> str:
        """构建 Discord 消息链接。"""
        return ThreadUpdateService.build_message_link(guild_id, thread_id, message_id)

    async def get_index_author_id(self, thread_id: int) -> int | None:
        """获取索引中记录的作品作者 ID。"""
        async with self.session_factory() as session:
            thread = await ThreadRepository(session).get_thread_with_tags(thread_id)
            return thread.author_id if thread else None

    async def get_update_by_overview(
        self, overview_message_id: int
    ) -> ThreadUpdateDTO | None:
        """按公开概览消息获取已发布更新。"""
        return await self.thread_update_service.get_by_overview_message_id(
            overview_message_id
        )

    async def _publish_message(
        self,
        thread: discord.Thread,
        message: discord.Message,
        description: str,
        version: str | None,
    ) -> ThreadUpdateDTO:
        """校验 Discord 来源消息后提交核心发布事务。"""
        author_id = await self.get_index_author_id(thread.id)
        if author_id is None:
            raise ThreadUpdateError("当前帖子未索引或已不可见")
        if message.author.id != author_id:
            raise ThreadUpdateError("更新消息不是索引作者发布的")
        return await self.thread_update_service.publish(
            thread_id=thread.id,
            message_id=message.id,
            publisher_id=author_id,
            description=description,
            version=version,
            source_message_at=message.created_at.replace(tzinfo=None),
        )

    async def publish_from_link(
        self,
        interaction: discord.Interaction,
        thread_id: int,
        message_link: str,
        description: str,
        version: str | None,
        *,
        send_overview: bool,
    ) -> ThreadUpdateDTO | None:
        """从交互提交的 Discord 链接发布作品更新。"""
        try:
            if not isinstance(interaction.channel, discord.Thread):
                raise ThreadUpdateError("此命令只能在 Discord 帖子中使用")
            if interaction.channel.id != thread_id:
                raise ThreadUpdateError("更新消息链接不属于当前帖子")
            author_id = await self.get_index_author_id(thread_id)
            if author_id is None:
                raise ThreadUpdateError("当前帖子未索引或已不可见")
            if interaction.user.id != author_id:
                raise ThreadUpdateError("你不是索引记录中的作品作者")
            match = self.MESSAGE_LINK_PATTERN.fullmatch(message_link.strip())
            if match is None:
                raise ThreadUpdateError("更新消息链接格式不正确")
            guild_id, link_thread_id, message_id = map(int, match.groups())
            if guild_id != interaction.guild_id or link_thread_id != thread_id:
                raise ThreadUpdateError("更新消息链接不属于当前服务器和帖子")
            try:
                source_message = await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.channel.fetch_message(message_id),
                    priority=3,
                )
            except (discord.NotFound, discord.Forbidden) as exc:
                raise ThreadUpdateError("更新消息不存在或 Bot 无权读取") from exc
            update = await self._publish_message(
                interaction.channel,
                source_message,
                description,
                version,
            )
            if send_overview:
                await self._send_auto_overview(source_message, update)
            await interaction.followup.send(
                f"已发布更新：{update.description}", ephemeral=True
            )
            return update
        except ThreadUpdateError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return None
        except Exception:
            logger.exception("发布作品更新失败: thread_id=%s", thread_id)
            await interaction.followup.send("发布失败，请稍后重试。", ephemeral=True)
            return None

    async def _send_auto_overview(
        self, source_message: discord.Message, update: ThreadUpdateDTO
    ) -> None:
        """尽力发送自动发布概览，失败不回滚数据库发布。"""
        message_link = source_message.jump_url
        embed = build_overview_embed(
            update.description,
            update.version,
            message_link,
        )
        try:
            overview = await self.bot.api_scheduler.submit(
                coro_factory=lambda: source_message.reply(
                    embed=embed,
                    view=AutoPublishOverviewView(self),
                ),
                priority=5,
            )
            await self.thread_update_service.set_overview_message_id(
                update.id, overview.id
            )
        except Exception:
            logger.warning(
                "自动发布已入库但发送概览失败: update_id=%s",
                update.id,
                exc_info=True,
            )

    async def edit_published_update(
        self,
        interaction: discord.Interaction,
        update_id: int,
        description: str,
        version: str | None,
    ) -> None:
        """修改发布信息并实时刷新已有公开概览。"""
        try:
            update = await self.thread_update_service.edit(
                update_id,
                interaction.user.id,
                description,
                version,
            )
            if interaction.message:
                message_link = None
                if update.message_id and interaction.guild_id:
                    message_link = self.build_message_link(
                        interaction.guild_id,
                        update.thread_id,
                        update.message_id,
                    )
                await interaction.message.edit(
                    embed=build_overview_embed(
                        update.description,
                        update.version,
                        message_link,
                    ),
                    view=AutoPublishOverviewView(self),
                )
            await interaction.followup.send("发布信息已更新。", ephemeral=True)
        except ThreadUpdateError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
        except Exception:
            logger.exception("修改发布信息失败: update_id=%s", update_id)
            await interaction.followup.send("修改失败，请稍后重试。", ephemeral=True)

    async def delete_published_update(
        self, interaction: discord.Interaction, update_id: int
    ) -> None:
        """撤销发布并更新公开概览状态。"""
        try:
            await self.thread_update_service.delete(update_id, interaction.user.id)
            if interaction.message:
                revoked_embed = discord.Embed(
                    title="更新发布概览",
                    description="此次发布已撤销。",
                    color=discord.Color.red(),
                )
                await interaction.message.edit(embed=revoked_embed, view=None)
            await interaction.followup.send("此次发布已删除。", ephemeral=True)
        except ThreadUpdateError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
        except Exception:
            logger.exception("删除发布失败: update_id=%s", update_id)
            await interaction.followup.send("删除失败，请稍后重试。", ephemeral=True)

    @app_commands.command(
        name="发布更新到索引页",
        description="将当前作品中的一条作者消息正式发布为更新",
    )
    @app_commands.describe(
        更新消息链接="当前帖子内的 Discord 消息链接",
        更新说明="展示给关注者的更新说明（1-500 字）",
        版本="可选版本号（1-50 字）",
    )
    async def publish_update_command(
        self,
        interaction: discord.Interaction,
        更新消息链接: str,
        更新说明: str,
        版本: str | None = None,
    ) -> None:
        """处理作者手动发布作品更新的应用命令。"""
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send(
                "此命令只能在 Discord 帖子中使用。", ephemeral=True
            )
            return
        await self.publish_from_link(
            interaction,
            interaction.channel.id,
            更新消息链接,
            更新说明,
            版本,
            send_overview=False,
        )

    async def set_user_auto_sync(
        self, user_id: int, thread_id: int, enabled: bool
    ) -> None:
        async with self.session_factory() as session:
            pref_repository = UserUpdatePreferenceRepository(session)
            await pref_repository.set_auto_sync(user_id, thread_id, enabled)

    async def set_user_no_remind(
        self, user_id: int, thread_id: int, enabled: bool
    ) -> None:
        async with self.session_factory() as session:
            pref_repository = UserUpdatePreferenceRepository(session)
            await pref_repository.set_no_remind(user_id, thread_id, enabled)

    # ── 用户指令：管理更新提醒偏好 ──

    update_remind_group = app_commands.Group(
        name="更新提醒设置", description="管理帖子更新检测的提醒偏好"
    )

    @update_remind_group.command(name="查看", description="查看当前帖子的更新提醒设置")
    async def view_preference(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        if not isinstance(interaction.channel, discord.Thread):
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 此命令只能在帖子中使用。", ephemeral=True
                ),
                priority=1,
            )
            return

        thread = interaction.channel
        async with self.session_factory() as session:
            pref_repository = UserUpdatePreferenceRepository(session)
            pref = await pref_repository.get_preference(interaction.user.id, thread.id)

        auto_sync = pref.auto_sync if pref else False
        no_remind = pref.no_remind if pref else False

        embed = discord.Embed(
            title="📦 更新提醒设置",
            description=f"帖子: **{thread.name}**",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="自动同步",
            value="✅ 已开启" if auto_sync else "❌ 未开启",
            inline=True,
        )
        embed.add_field(
            name="更新提醒",
            value="🔕 已关闭" if no_remind else "🔔 已开启",
            inline=True,
        )
        embed.set_footer(text="使用 /更新提醒设置 修改 来更改这些设置")

        await self.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.followup.send(embed=embed, ephemeral=True),
            priority=1,
        )

    @update_remind_group.command(name="修改", description="修改当前帖子的更新提醒设置")
    @app_commands.describe(
        自动同步="是否自动同步更新到索引页（无需确认）",
        不再提醒="是否关闭此帖的更新检测提醒",
    )
    @app_commands.choices(
        自动同步=[
            app_commands.Choice(name="开启", value=1),
            app_commands.Choice(name="关闭", value=0),
        ],
        不再提醒=[
            app_commands.Choice(name="开启（不再提醒）", value=1),
            app_commands.Choice(name="关闭（恢复提醒）", value=0),
        ],
    )
    async def modify_preference(
        self,
        interaction: discord.Interaction,
        自动同步: app_commands.Choice[int] | None = None,
        不再提醒: app_commands.Choice[int] | None = None,
    ):
        await safe_defer(interaction)

        if not isinstance(interaction.channel, discord.Thread):
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 此命令只能在帖子中使用。", ephemeral=True
                ),
                priority=1,
            )
            return

        thread = interaction.channel

        if 自动同步 is None and 不再提醒 is None:
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 请至少指定一个设置项。", ephemeral=True
                ),
                priority=1,
            )
            return

        changes = []
        async with self.session_factory() as session:
            pref_repository = UserUpdatePreferenceRepository(session)

            if 自动同步 is not None:
                enabled = 自动同步.value == 1
                await pref_repository.set_auto_sync(
                    interaction.user.id, thread.id, enabled
                )
                changes.append(f"自动同步: {'✅ 已开启' if enabled else '❌ 已关闭'}")

            if 不再提醒 is not None:
                enabled = 不再提醒.value == 1
                await pref_repository.set_no_remind(
                    interaction.user.id, thread.id, enabled
                )
                changes.append(f"更新提醒: {'🔕 已关闭' if enabled else '🔔 已恢复'}")

        result_text = "\n".join(changes)
        await self.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.followup.send(
                f"✅ 设置已更新：\n{result_text}", ephemeral=True
            ),
            priority=1,
        )

    @update_remind_group.command(
        name="重置", description="重置当前帖子的更新提醒设置为默认值"
    )
    async def reset_preference(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        if not isinstance(interaction.channel, discord.Thread):
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 此命令只能在帖子中使用。", ephemeral=True
                ),
                priority=1,
            )
            return

        thread = interaction.channel
        async with self.session_factory() as session:
            pref_repository = UserUpdatePreferenceRepository(session)
            success = await pref_repository.reset_preference(
                interaction.user.id, thread.id
            )

        if success:
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "✅ 已重置为默认设置（提醒开启、自动同步关闭）。",
                    ephemeral=True,
                ),
                priority=1,
            )
        else:
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "ℹ️ 当前帖子没有自定义设置，无需重置。", ephemeral=True
                ),
                priority=1,
            )
