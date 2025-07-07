import discord
from discord import app_commands
from discord.ext import commands
import datetime

from search import database


class TagSystem(commands.Cog):
    """处理标签同步与评价"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.indexed_channel_ids = set()  # 缓存已索引的频道ID

    async def cog_load(self):
        """Cog加载时初始化缓存"""
        await self.refresh_indexed_channels_cache()

    async def refresh_indexed_channels_cache(self):
        """刷新已索引频道的缓存"""
        self.indexed_channel_ids = set(await database.get_indexed_channel_ids())
        print(self.indexed_channel_ids)

    def is_channel_indexed(self, channel_id: int) -> bool:
        """检查频道是否已索引"""
        return channel_id in self.indexed_channel_ids

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        # 只处理已索引频道中的帖子
        if self.is_channel_indexed(thread.parent_id):
            await self.sync_thread(thread)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if before.applied_tags != after.applied_tags:
            # 只处理已索引频道中的帖子
            if self.is_channel_indexed(after.parent_id):
                await self.sync_thread(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if isinstance(message.channel, discord.Thread):
            # 只处理已索引频道中的帖子
            thread = message.channel
            if self.is_channel_indexed(thread.parent_id):
                # 更新活跃时间和回复数
                await self._update_thread_basic_info(thread, message.created_at)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread):
                # 只处理已索引频道中的帖子
                if self.is_channel_indexed(channel.parent_id):
                    # 如果是首楼消息被编辑，需要重新同步整个帖子
                    if payload.message_id == channel.id:
                        await self.sync_thread(channel)
                    else:
                        # 普通消息编辑只更新活跃时间
                        # 由于是raw事件，没有具体的编辑时间，使用当前时间
                        await self._update_thread_basic_info(channel, datetime.datetime.now(datetime.timezone.utc))
        except Exception as e:
            print(f"处理消息编辑事件失败: {e}")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread):
                # 只处理已索引频道中的帖子
                if self.is_channel_indexed(channel.parent_id):
                    # 如果首楼被删除，删除整个索引
                    if payload.message_id == channel.id:
                        await self._delete_thread_index(channel.id)
                    else:
                        # 普通消息删除，更新回复数和活跃时间
                        await self._update_thread_basic_info(channel)
        except Exception as e:
            print(f"处理消息删除事件失败: {e}")

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        # 只处理已索引频道中的帖子
        if self.is_channel_indexed(thread.parent_id):
            await self._delete_thread_index(thread.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread):
                # 只处理已索引频道中的帖子
                if self.is_channel_indexed(channel.parent_id):
                    await self._update_reaction_count_by_channel(channel)
        except Exception as e:
            print(f"处理反应添加事件失败: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread):
                # 只处理已索引频道中的帖子
                if self.is_channel_indexed(channel.parent_id):
                    await self._update_reaction_count_by_channel(channel)
        except Exception as e:
            print(f"处理反应移除事件失败: {e}")

    async def _update_thread_basic_info(self, thread: discord.Thread, last_active_time=None):
        """更新帖子基本信息（活跃时间、回复数等），不更新首楼内容"""
        if last_active_time is None:
            last_active_time = thread.created_at
        
        # 获取现有的首楼摘要、缩略图和反应数（避免重复抓取和重置）
        existing_data = await database.get_thread_basic_info(thread.id)
        excerpt = existing_data.get('first_message_excerpt', '') if existing_data else ''
        thumbnail_url = existing_data.get('thumbnail_url', '') if existing_data else ''
        reaction_count = existing_data.get('reaction_count', 0) if existing_data else 0
        
        await database.add_or_update_thread({
            "thread_id": thread.id,
            "channel_id": thread.parent_id,
            "title": thread.name,
            "author_id": thread.owner_id or 0,
            "created_at": str(thread.created_at),
            "last_active_at": str(last_active_time),
            "reaction_count": reaction_count,  # 保留现有的反应数，不重置
            "reply_count": thread.message_count,
            "tags": ", ".join([t.name for t in thread.applied_tags or []]),
            "first_message_excerpt": excerpt,
            "thumbnail_url": thumbnail_url
        })

    async def _delete_thread_index(self, thread_id: int):
        """删除帖子索引和相关数据"""
        await database.delete_thread_index(thread_id)
        # 刷新缓存，因为可能该频道已无任何索引帖子
        await self.refresh_indexed_channels_cache()

    async def _update_reaction_count_by_channel(self, thread: discord.Thread):
        """通过频道更新反应数量（用于raw事件）"""
        # 获取首楼消息的最高反应数
        try:
            first_msg = await thread.fetch_message(thread.id)
            reaction_count = max([r.count for r in first_msg.reactions]) if first_msg.reactions else 0
        except Exception as e:
            print(f"获取首楼消息的最高反应数失败: {e}")
            reaction_count = 0
        
        # 获取现有数据以保持首楼摘要等信息
        existing_data = await database.get_thread_basic_info(thread.id)
        excerpt = existing_data.get('first_message_excerpt', '') if existing_data else ''
        thumbnail_url = existing_data.get('thumbnail_url', '') if existing_data else ''
        
        await database.add_or_update_thread({
            "thread_id": thread.id,
            "channel_id": thread.parent_id,
            "title": thread.name,
            "author_id": thread.owner_id or 0,
            "created_at": str(thread.created_at),
            "last_active_at": str(thread.created_at),  # 这里使用thread的创建时间，因为没有具体的反应时间
            "reaction_count": reaction_count,
            "reply_count": thread.message_count,
            "tags": ", ".join([t.name for t in thread.applied_tags or []]),
            "first_message_excerpt": excerpt,
            "thumbnail_url": thumbnail_url
        })

    async def sync_thread(self, thread: discord.Thread):
        # 将频道添加到已索引缓存中
        self.indexed_channel_ids.add(thread.parent_id)
        
        tags = thread.applied_tags or []
        tag_names = [t.name for t in tags]
        excerpt = ""
        attach_url = ""
        reaction_count = 0
        try:
            first_msg = await thread.fetch_message(thread.id)
            if first_msg:
                excerpt = first_msg.content  # 存储完整内容，不截取
                if first_msg.attachments:
                    attach_url = first_msg.attachments[0].url
                # 统计首楼消息的最高反应数
                reaction_count = max([r.count for r in first_msg.reactions]) if first_msg.reactions else 0
        except Exception:
            pass

        thread_info = {
            "thread_id": thread.id,
            "channel_id": thread.parent_id,
            "title": thread.name,
            "author_id": thread.owner_id or 0,
            "created_at": str(thread.created_at),
            "last_active_at": str(thread.created_at),
            "reaction_count": reaction_count,
            "reply_count": thread.message_count,
            "tags": ", ".join(tag_names),
            "first_message_excerpt": excerpt,
            "thumbnail_url": attach_url
        }
        await database.add_or_update_thread(thread_info)
        for t in tags:
            await database.ensure_tag(t.id, t.name)
            await database.link_thread_tag(thread.id, t.id)

    @app_commands.command(name="标签评价", description="给当前帖子标签点赞或点踩")
    async def tag_rate(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            await interaction.response.send_message("此命令需在帖子内使用。", ephemeral=True)
            return

        tags = channel.applied_tags
        if not tags:
            await interaction.response.send_message("此帖子无标签。", ephemeral=True)
            return

        view = TagVoteView(tags)
        await interaction.response.send_message("请选择对标签的评价：", view=view, ephemeral=True)

    @app_commands.command(name="查看帖子标签", description="查看当前帖子标签评价")
    async def check_tag_stats(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            await interaction.response.send_message("此命令需在帖子内使用。", ephemeral=True)
            return
        stats = await database.get_tag_vote_stats(channel.id)
        if not stats:
            await interaction.response.send_message("暂无评价数据。", ephemeral=True)
            return
        lines = [f"**{row[0]}** - 👍 {row[1] or 0} | 👎 {row[2] or 0} | 总分 {row[3]}" for row in stats]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

class TagVoteView(discord.ui.View):
    def __init__(self, tags):
        super().__init__(timeout=60)
        # 第一行：所有标签的点赞按钮
        for tag in tags:
            self.add_item(TagVoteButton(tag, True, row=0))
        # 第二行：所有标签的点踩按钮
        for tag in tags:
            self.add_item(TagVoteButton(tag, False, row=1))

class TagVoteButton(discord.ui.Button):
    def __init__(self, tag, up: bool, row: int = 0):
        self.tag = tag
        self.vote_value = 1 if up else -1
        label = f"{'👍' if up else '👎'} {tag.name}"
        super().__init__(label=label, style=discord.ButtonStyle.green if up else discord.ButtonStyle.red, row=row)

    async def callback(self, interaction: discord.Interaction):
        await database.record_tag_vote(interaction.user.id, self.tag.id, self.vote_value)
        await interaction.response.send_message("已记录您的评价！", ephemeral=True) 