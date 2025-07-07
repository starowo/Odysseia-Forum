import discord
from discord import app_commands
from discord.ext import commands

class Indexer(commands.Cog):
    """构建索引相关命令"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="构建索引", description="对当前论坛频道的所有帖子进行索引")
    async def build_index(self, interaction: discord.Interaction):
        channel = interaction.channel.parent
        if not isinstance(channel, discord.ForumChannel):
            await interaction.response.send_message("请在论坛频道内使用此命令。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        count = 0

        # 活跃线程
        for thread in channel.threads:
            await self._process_thread(thread)
            count += 1

        # 已归档线程 - 分页处理
        before = None
        page_count = 0
        
        while True:
            try:
                archived_threads = []
                async for thread in channel.archived_threads(limit=100, before=before):
                    archived_threads.append(thread)
                
                if len(archived_threads) == 0:
                    break
                    
                # 处理这一页的归档线程
                for thread in archived_threads:
                    await self._process_thread(thread)
                    count += 1
                
                # 更新before为最后一个线程的归档时间
                if archived_threads:
                    before = archived_threads[-1].archive_timestamp
                    page_count += 1
                    
                    # 每处理1页更新一次进度
                    if page_count % 1 == 0:
                        await interaction.edit_original_response(content=f"正在索引归档线程...已处理 {page_count} 页，共索引 {count} 个帖子")
                else:
                    break
                    
            except Exception as e:
                print(f"获取归档线程失败: {e}")
                break

        await interaction.followup.send(f"已索引 {count} 个帖子（包含 {page_count} 页归档线程）。", ephemeral=True)

        # 通知TagSystem刷新缓存
        tag_system = self.bot.get_cog("TagSystem")
        if tag_system:
            await tag_system.refresh_indexed_channels_cache()

    async def _process_thread(self, thread: discord.Thread):
        tag_cog = self.bot.get_cog("TagSystem")
        if tag_cog:
            await tag_cog.sync_thread(thread) 