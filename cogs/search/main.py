import discord
from discord import app_commands
from discord.ext import commands
import datetime

import database
from ranking_config import RankingConfig
from .views import (
    PersistentChannelSearchView, PersistentGlobalSearchView, AuthorTagSelectionView,
    SearchResultsView, CombinedSearchView, ChannelSelectionView
)

class Search(commands.Cog):
    """搜索相关命令"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_tags_cache = {}  # 缓存频道tags

    async def cog_load(self):
        """在Cog加载时注册持久化View"""
        # 注册持久化view，使其在bot重启后仍能响应
        self.bot.add_view(PersistentChannelSearchView(None))  # None作为占位符
        self.bot.add_view(PersistentGlobalSearchView())
        
        # 缓存频道tags
        await self.cache_channel_tags()

    async def cache_channel_tags(self):
        """缓存所有已索引频道的tags"""
        try:
            # 获取已索引的频道ID
            indexed_channel_ids = await database.get_indexed_channel_ids()
            
            self.channel_tags_cache = {}
            
            for guild in self.bot.guilds:
                for channel in guild.channels:
                    if isinstance(channel, discord.ForumChannel) and channel.id in indexed_channel_ids:
                        # 获取频道的所有可用标签
                        tags = {}
                        for tag in channel.available_tags:
                            tags[tag.name] = tag.id
                        self.channel_tags_cache[channel.id] = tags
                        
            print(f"已缓存 {len(self.channel_tags_cache)} 个频道的tags")
            
        except Exception as e:
            print(f"缓存频道tags时出错: {e}")

    def get_merged_tags(self, channel_ids: list[int]) -> list[tuple[int, str]]:
        """获取多个频道的合并tags，重名tag会被合并显示"""
        all_tags_names = set()
        
        for channel_id in channel_ids:
            channel_tags = self.channel_tags_cache.get(channel_id, {})
            all_tags_names.update(channel_tags.keys())
        
        # 返回合并后的tag列表，使用tag名称作为唯一标识
        # tag_id设为0，因为我们主要用tag名称进行搜索
        return [(0, tag_name) for tag_name in sorted(all_tags_names)]

    # ----- 用户偏好设置 -----
    @app_commands.command(name="每页结果数量", description="设置每页展示的搜索结果数量（3-10）")
    @app_commands.describe(num="数字 3-10")
    async def set_page_size(self, interaction: discord.Interaction, num: int):
        if not 3 <= num <= 10:
            await interaction.response.send_message("请输入 3-10 之间的数字。", ephemeral=True)
            return
        await database.set_results_per_page(interaction.user.id, num)
        await interaction.response.send_message(f"已将每页结果数量设置为 {num}。", ephemeral=True)

    # ----- 搜索偏好设置 -----
    search_prefs = app_commands.Group(name="搜索偏好", description="管理搜索偏好设置")
    
    @search_prefs.command(name="作者", description="管理作者偏好设置")
    @app_commands.describe(
        action="操作类型",
        user="要设置的用户（@用户 或 用户ID）"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="只看作者", value="include_author"),
        app_commands.Choice(name="屏蔽作者", value="exclude_author"),
        app_commands.Choice(name="取消屏蔽", value="unblock_author"),
        app_commands.Choice(name="清空作者偏好", value="clear_authors")
    ])
    async def search_preferences_author(
        self, 
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        user: discord.User = None
    ):
        user_id = interaction.user.id
        
        try:
            if action.value == "include_author":
                if not user:
                    await interaction.response.send_message("❌ 请指定要设置的用户。", ephemeral=True)
                    return
                
                prefs = await database.get_user_search_preferences(user_id)
                include_authors = set(prefs['include_authors'] or [])
                exclude_authors = set(prefs['exclude_authors'] or [])
                
                # 添加到只看作者列表，从屏蔽列表中移除
                include_authors.add(user.id)
                exclude_authors.discard(user.id)
                
                await database.save_user_search_preferences(
                    user_id, list(include_authors), list(exclude_authors),
                    prefs['after_date'], prefs['before_date'], prefs['tag_logic'], prefs['preview_image_mode']
                )
                
                await interaction.response.send_message(
                    f"✅ 已将 {user.mention} 添加到只看作者列表。", ephemeral=True
                )
            
            elif action.value == "exclude_author":
                if not user:
                    await interaction.response.send_message("❌ 请指定要屏蔽的用户。", ephemeral=True)
                    return
                
                prefs = await database.get_user_search_preferences(user_id)
                include_authors = set(prefs['include_authors'] or [])
                exclude_authors = set(prefs['exclude_authors'] or [])
                
                # 添加到屏蔽列表，从只看作者列表中移除
                exclude_authors.add(user.id)
                include_authors.discard(user.id)
                
                await database.save_user_search_preferences(
                    user_id, list(include_authors), list(exclude_authors),
                    prefs['after_date'], prefs['before_date'], prefs['tag_logic'], prefs['preview_image_mode']
                )
                
                await interaction.response.send_message(
                    f"✅ 已将 {user.mention} 添加到屏蔽作者列表。", ephemeral=True
                )
            
            elif action.value == "unblock_author":
                if not user:
                    await interaction.response.send_message("❌ 请指定要取消屏蔽的用户。", ephemeral=True)
                    return
                
                prefs = await database.get_user_search_preferences(user_id)
                include_authors = set(prefs['include_authors'] or [])
                exclude_authors = set(prefs['exclude_authors'] or [])
                
                # 从屏蔽列表中移除
                if user.id in exclude_authors:
                    exclude_authors.remove(user.id)
                    await database.save_user_search_preferences(
                        user_id, list(include_authors), list(exclude_authors),
                        prefs['after_date'], prefs['before_date'], prefs['tag_logic'], prefs['preview_image_mode']
                    )
                    await interaction.response.send_message(
                        f"✅ 已将 {user.mention} 从屏蔽列表中移除。", ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"ℹ️ {user.mention} 不在屏蔽列表中。", ephemeral=True
                    )
            
            elif action.value == "clear_authors":
                prefs = await database.get_user_search_preferences(user_id)
                await database.save_user_search_preferences(
                    user_id, [], [], prefs['after_date'], prefs['before_date'], prefs['tag_logic'], prefs['preview_image_mode']
                )
                await interaction.response.send_message("✅ 已清空所有作者偏好设置。", ephemeral=True)
        
        except Exception as e:
            await interaction.response.send_message(f"❌ 操作失败：{e}", ephemeral=True)

    @search_prefs.command(name="时间", description="设置搜索时间范围偏好")
    @app_commands.describe(
        after_date="开始日期（格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）",
        before_date="结束日期（格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）"
    )
    async def search_preferences_time(
        self, 
        interaction: discord.Interaction,
        after_date: str = None,
        before_date: str = None
    ):
        user_id = interaction.user.id
        
        try:
            # 解析时间
            parsed_after = None
            parsed_before = None
            
            if after_date:
                try:
                    date_str = after_date.strip()
                    if len(date_str) == 10:  # YYYY-MM-DD
                        date_str += " 00:00:00"
                    parsed_after = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").isoformat()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ 开始日期格式错误，请使用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS 格式。", ephemeral=True
                    )
                    return
            
            if before_date:
                try:
                    date_str = before_date.strip()
                    if len(date_str) == 10:  # YYYY-MM-DD
                        date_str += " 23:59:59"
                    parsed_before = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").isoformat()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ 结束日期格式错误，请使用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS 格式。", ephemeral=True
                    )
                    return
            
            # 检查日期逻辑
            if parsed_after and parsed_before and parsed_after > parsed_before:
                await interaction.response.send_message("❌ 开始日期不能晚于结束日期。", ephemeral=True)
                return
            
            prefs = await database.get_user_search_preferences(user_id)
            await database.save_user_search_preferences(
                user_id, prefs['include_authors'], prefs['exclude_authors'],
                parsed_after, parsed_before, prefs['tag_logic'], prefs['preview_image_mode']
            )
            
            # 根据参数情况给出不同的反馈
            if not after_date and not before_date:
                # 没有填任何参数，清空时间范围设置
                await interaction.response.send_message("✅ 已清空时间范围设置。", ephemeral=True)
            else:
                # 设置了时间参数
                time_info = []
                if parsed_after:
                    time_info.append(f"开始时间：{after_date}")
                if parsed_before:
                    time_info.append(f"结束时间：{before_date}")
                
                await interaction.response.send_message(
                    f"✅ 已设置时间范围：\n" + "\n".join(time_info), ephemeral=True
                )
        
        except Exception as e:
            await interaction.response.send_message(f"❌ 操作失败：{e}", ephemeral=True)

    @search_prefs.command(name="标签", description="设置多选标签逻辑偏好")
    @app_commands.describe(
        logic="标签逻辑类型"
    )
    @app_commands.choices(logic=[
        app_commands.Choice(name="同时（必须包含所有选择的标签）", value="同时"),
        app_commands.Choice(name="任一（只需包含任意一个选择的标签）", value="任一")
    ])
    async def search_preferences_tag(
        self, 
        interaction: discord.Interaction,
        logic: app_commands.Choice[str]
    ):
        user_id = interaction.user.id
        
        try:
            # 转换为内部格式
            tag_logic_internal = "and" if logic.value == "同时" else "or"
            
            prefs = await database.get_user_search_preferences(user_id)
            await database.save_user_search_preferences(
                user_id, prefs['include_authors'], prefs['exclude_authors'],
                prefs['after_date'], prefs['before_date'], tag_logic_internal, prefs['preview_image_mode']
            )
            
            await interaction.response.send_message(
                f"✅ 已设置多选标签逻辑为：**{logic.value}**\n"
                f"• 同时：必须包含所有选择的标签\n"
                f"• 任一：只需包含任意一个选择的标签",
                ephemeral=True
            )
        
        except Exception as e:
            await interaction.response.send_message(f"❌ 操作失败：{e}", ephemeral=True)

    @search_prefs.command(name="预览图", description="设置搜索结果预览图显示方式")
    @app_commands.describe(
        mode="预览图显示方式"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="缩略图（右侧小图）", value="thumbnail"),
        app_commands.Choice(name="大图（下方大图）", value="image")
    ])
    async def search_preferences_preview(
        self, 
        interaction: discord.Interaction,
        mode: app_commands.Choice[str]
    ):
        user_id = interaction.user.id
        
        try:
            prefs = await database.get_user_search_preferences(user_id)
            await database.save_user_search_preferences(
                user_id, prefs['include_authors'], prefs['exclude_authors'],
                prefs['after_date'], prefs['before_date'], prefs['tag_logic'], mode.value
            )
            
            await interaction.response.send_message(
                f"✅ 已设置预览图显示方式为：**{mode.name}**\n"
                f"• 缩略图：在搜索结果右侧显示小图\n"
                f"• 大图：在搜索结果下方显示大图",
                ephemeral=True
            )
        
        except Exception as e:
            await interaction.response.send_message(f"❌ 操作失败：{e}", ephemeral=True)

    @search_prefs.command(name="查看", description="查看当前搜索偏好设置")
    async def search_preferences_view(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        try:
            prefs = await database.get_user_search_preferences(user_id)
            
            embed = discord.Embed(
                title="🔍 当前搜索偏好设置",
                color=0x3498db
            )
            
            # 作者偏好
            author_info = []
            if prefs['include_authors']:
                authors = [f"<@{uid}>" for uid in prefs['include_authors']]
                author_info.append(f"**只看作者：** {', '.join(authors)}")
            
            if prefs['exclude_authors']:
                authors = [f"<@{uid}>" for uid in prefs['exclude_authors']]
                author_info.append(f"**屏蔽作者：** {', '.join(authors)}")
            
            if not author_info:
                author_info.append("**作者偏好：** 无限制")
            
            embed.add_field(
                name="作者设置",
                value="\n".join(author_info),
                inline=False
            )
            
            # 时间偏好
            time_info = []
            if prefs['after_date']:
                after_dt = datetime.datetime.fromisoformat(prefs['after_date'])
                time_info.append(f"**开始时间：** {after_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if prefs['before_date']:
                before_dt = datetime.datetime.fromisoformat(prefs['before_date'])
                time_info.append(f"**结束时间：** {before_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if not time_info:
                time_info.append("**时间范围：** 无限制")
            
            embed.add_field(
                name="时间设置",
                value="\n".join(time_info),
                inline=False
            )
            
            # 标签逻辑设置
            tag_logic_display = "同时" if prefs['tag_logic'] == "and" else "任一"
            embed.add_field(
                name="标签逻辑",
                value=f"**多选标签逻辑：** {tag_logic_display}\n"
                      f"• 同时：必须包含所有选择的标签\n"
                      f"• 任一：只需包含任意一个选择的标签",
                inline=False
            )
            
            # 预览图设置
            preview_mode = prefs.get('preview_image_mode', 'thumbnail')
            preview_display = "缩略图（右侧小图）" if preview_mode == "thumbnail" else "大图（下方大图）"
            embed.add_field(
                name="预览图设置",
                value=f"**预览图显示方式：** {preview_display}\n"
                      f"• 缩略图：在搜索结果右侧显示小图\n"
                      f"• 大图：在搜索结果下方显示大图",
                inline=False
            )
            
            embed.set_footer(text="使用 /搜索偏好 子命令来修改这些设置")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            await interaction.response.send_message(f"❌ 操作失败：{e}", ephemeral=True)

    @search_prefs.command(name="清空", description="清空所有搜索偏好设置")
    async def search_preferences_clear(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        try:
            await database.save_user_search_preferences(
                user_id, [], [], None, None, "and", "thumbnail"
            )
            
            await interaction.response.send_message("✅ 已清空所有搜索偏好设置。", ephemeral=True)
        
        except Exception as e:
            await interaction.response.send_message(f"❌ 操作失败：{e}", ephemeral=True)

    # ----- 排序算法管理 -----
    @app_commands.command(name="排序算法配置", description="管理员设置搜索排序算法参数")
    @app_commands.describe(
        preset="预设配置方案",
        time_weight="时间权重因子 (0.0-1.0)",
        tag_weight="标签权重因子 (0.0-1.0)",
        reaction_weight="反应权重因子 (0.0-1.0)",
        time_decay="时间衰减率 (0.01-0.5)",
        reaction_log_base="反应数对数基数 (10-200)",
        severe_penalty="严重惩罚阈值 (0.0-1.0)",
        mild_penalty="轻度惩罚阈值 (0.0-1.0)"
    )
    @app_commands.choices(preset=[
        app_commands.Choice(name="平衡配置 (默认)", value="balanced"),
        app_commands.Choice(name="偏重时间新鲜度", value="time_focused"),
        app_commands.Choice(name="偏重内容质量", value="quality_focused"),
        app_commands.Choice(name="偏重受欢迎程度", value="popularity_focused"),
        app_commands.Choice(name="严格质量控制", value="strict_quality")
    ])
    async def configure_ranking(
        self, 
        interaction: discord.Interaction,
        preset: app_commands.Choice[str] = None,
        time_weight: float = None,
        tag_weight: float = None,
        reaction_weight: float = None,
        time_decay: float = None,
        reaction_log_base: int = None,
        severe_penalty: float = None,
        mild_penalty: float = None
    ):
        # 检查权限 (需要管理员权限)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("此命令需要管理员权限。", ephemeral=True)
            return

        try:
            # 应用预设配置
            if preset:
                from ranking_config import PresetConfigs
                if preset.value == "balanced":
                    PresetConfigs.balanced()
                elif preset.value == "time_focused":
                    PresetConfigs.time_focused()
                elif preset.value == "quality_focused":
                    PresetConfigs.quality_focused()
                elif preset.value == "popularity_focused":
                    PresetConfigs.popularity_focused()
                elif preset.value == "strict_quality":
                    PresetConfigs.strict_quality()
                
                config_name = preset.name
            else:
                # 手动配置参数
                if time_weight is not None:
                    if 0 <= time_weight <= 1:
                        RankingConfig.TIME_WEIGHT_FACTOR = time_weight
                    else:
                        raise ValueError("时间权重必须在0-1之间")
                
                if tag_weight is not None:
                    if 0 <= tag_weight <= 1:
                        RankingConfig.TAG_WEIGHT_FACTOR = tag_weight
                    else:
                        raise ValueError("标签权重必须在0-1之间")
                
                if reaction_weight is not None:
                    if 0 <= reaction_weight <= 1:
                        RankingConfig.REACTION_WEIGHT_FACTOR = reaction_weight
                    else:
                        raise ValueError("反应权重必须在0-1之间")
                
                # 确保权重和为1 (三个权重)
                if time_weight is not None or tag_weight is not None or reaction_weight is not None:
                    # 计算当前权重总和
                    current_total = RankingConfig.TIME_WEIGHT_FACTOR + RankingConfig.TAG_WEIGHT_FACTOR + RankingConfig.REACTION_WEIGHT_FACTOR
                    
                    # 如果权重和不为1，按比例重新分配
                    if abs(current_total - 1.0) > 0.001:
                        RankingConfig.TIME_WEIGHT_FACTOR = RankingConfig.TIME_WEIGHT_FACTOR / current_total
                        RankingConfig.TAG_WEIGHT_FACTOR = RankingConfig.TAG_WEIGHT_FACTOR / current_total
                        RankingConfig.REACTION_WEIGHT_FACTOR = RankingConfig.REACTION_WEIGHT_FACTOR / current_total
                
                if time_decay is not None:
                    if 0.01 <= time_decay <= 0.5:
                        RankingConfig.TIME_DECAY_RATE = time_decay
                    else:
                        raise ValueError("时间衰减率必须在0.01-0.5之间")
                
                if reaction_log_base is not None:
                    if 10 <= reaction_log_base <= 200:
                        RankingConfig.REACTION_LOG_BASE = reaction_log_base
                    else:
                        raise ValueError("反应数对数基数必须在10-200之间")
                
                if severe_penalty is not None:
                    if 0 <= severe_penalty <= 1:
                        RankingConfig.SEVERE_PENALTY_THRESHOLD = severe_penalty
                    else:
                        raise ValueError("严重惩罚阈值必须在0-1之间")
                
                if mild_penalty is not None:
                    if 0 <= mild_penalty <= 1:
                        RankingConfig.MILD_PENALTY_THRESHOLD = mild_penalty
                    else:
                        raise ValueError("轻度惩罚阈值必须在0-1之间")
                
                config_name = "自定义配置"
            
            # 验证配置
            RankingConfig.validate()
            
            # 构建响应消息
            embed = discord.Embed(
                title="✅ 排序算法配置已更新",
                description=f"当前配置：**{config_name}**",
                color=0x00ff00
            )
            
            embed.add_field(
                name="权重配置",
                value=f"• 时间权重：**{RankingConfig.TIME_WEIGHT_FACTOR:.1%}**\n"
                      f"• 标签权重：**{RankingConfig.TAG_WEIGHT_FACTOR:.1%}**\n"
                      f"• 反应权重：**{RankingConfig.REACTION_WEIGHT_FACTOR:.1%}**\n"
                      f"• 时间衰减率：**{RankingConfig.TIME_DECAY_RATE}**\n"
                      f"• 反应对数基数：**{RankingConfig.REACTION_LOG_BASE}**",
                inline=True
            )
            
            embed.add_field(
                name="惩罚机制",
                value=f"• 严重惩罚阈值：**{RankingConfig.SEVERE_PENALTY_THRESHOLD}**\n"
                      f"• 轻度惩罚阈值：**{RankingConfig.MILD_PENALTY_THRESHOLD}**\n"
                      f"• 严重惩罚系数：**{RankingConfig.SEVERE_PENALTY_FACTOR}**",
                inline=True
            )
            
            # 添加算法说明
            embed.add_field(
                name="算法说明",
                value="新的排序算法将立即生效，影响所有后续搜索结果。\n"
                      "时间权重基于指数衰减，标签权重基于Wilson Score算法。",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.response.send_message(f"❌ 配置错误：{e}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 配置失败：{e}", ephemeral=True)

    @app_commands.command(name="查看排序配置", description="查看当前搜索排序算法配置")
    async def view_ranking_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔧 当前排序算法配置",
            description="智能混合权重排序算法参数",
            color=0x3498db
        )
        
        embed.add_field(
            name="权重配置",
            value=f"• 时间权重：**{RankingConfig.TIME_WEIGHT_FACTOR:.1%}**\n"
                  f"• 标签权重：**{RankingConfig.TAG_WEIGHT_FACTOR:.1%}**\n"
                  f"• 反应权重：**{RankingConfig.REACTION_WEIGHT_FACTOR:.1%}**\n"
                  f"• 时间衰减率：**{RankingConfig.TIME_DECAY_RATE}**\n"
                  f"• 反应对数基数：**{RankingConfig.REACTION_LOG_BASE}**",
            inline=True
        )
        
        embed.add_field(
            name="惩罚机制",
            value=f"• 严重惩罚阈值：**{RankingConfig.SEVERE_PENALTY_THRESHOLD}**\n"
                  f"• 轻度惩罚阈值：**{RankingConfig.MILD_PENALTY_THRESHOLD}**\n"
                  f"• 严重惩罚系数：**{RankingConfig.SEVERE_PENALTY_FACTOR:.1%}**\n"
                  f"• 轻度惩罚系数：**{RankingConfig.MILD_PENALTY_FACTOR:.1%}**",
            inline=True
        )
        
        embed.add_field(
            name="算法特性",
            value="• **Wilson Score**：置信度评估标签质量\n"
                  "• **指数衰减**：时间新鲜度自然衰减\n"
                  "• **智能惩罚**：差评内容自动降权\n"
                  "• **可配置权重**：灵活调整排序偏好",
            inline=False
        )
        
        embed.set_footer(text="管理员可使用 /排序算法配置 命令调整参数")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----- 创建搜索按钮 -----
    @app_commands.command(name="创建频道搜索", description="在当前帖子内创建频道搜索按钮")
    async def create_channel_search(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("请在帖子内使用此命令。", ephemeral=True)
            return
        
        # 刷新缓存
        await self.cache_channel_tags()
        
        # 获取父频道ID用于搜索
        channel_id = interaction.channel.parent_id
        view = PersistentChannelSearchView(channel_id)
        
        # 创建美观的embed
        embed = discord.Embed(
            title="🔍 频道搜索",
            description=f"搜索 <#{channel_id}> 频道中的所有帖子",
            color=0x3498db
        )
        embed.add_field(
            name="使用方法",
            value="点击下方按钮开始搜索，可以按标签、关键词等条件筛选帖子",
            inline=False
        )
        
        await interaction.response.send_message("✅ 已创建频道搜索按钮。", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="创建全局搜索", description="在当前频道创建全局搜索按钮")
    async def create_global_search(self, interaction: discord.Interaction):
        # 刷新缓存
        await self.cache_channel_tags()
        
        view = PersistentGlobalSearchView()
        
        # 创建美观的embed
        embed = discord.Embed(
            title="🌐 全局搜索",
            description="搜索服务器内所有论坛频道的帖子",
            color=0x2ecc71
        )
        embed.add_field(
            name="使用方法",
            value="1. 点击下方按钮选择要搜索的论坛频道\n2. 设置搜索条件（标签、关键词等）\n3. 查看搜索结果",
            inline=False
        )
        
        await interaction.response.send_message("✅ 已创建全局搜索按钮。", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="全局搜索", description="开始一次仅自己可见的全局搜索")
    async def global_search(self, interaction: discord.Interaction):
        """直接触发全局搜索流程"""
        view = PersistentGlobalSearchView()
        await view.start_search_flow(interaction)

    @app_commands.command(name="快捷搜索", description="快速搜索指定作者的所有帖子")
    @app_commands.describe(author="要搜索的作者（@用户 或 用户ID）")
    async def quick_author_search(self, interaction: discord.Interaction, author: discord.User):
        await interaction.response.defer(ephemeral=True)
        
        # 刷新缓存
        await self.cache_channel_tags()
        
        # 获取所有已索引的频道ID
        indexed_channel_ids = await database.get_indexed_channel_ids()
        
        if not indexed_channel_ids:
            await interaction.followup.send("暂无已索引的论坛频道。", ephemeral=True)
            return
        
        # 创建作者搜索视图并执行初始搜索
        view = AuthorTagSelectionView(indexed_channel_ids, author.id)
        initial_results = await view.setup_with_initial_search(interaction.guild, interaction.user.id)
        
        if not initial_results['has_results']:
            # 没有搜索结果时
            if 'error' in initial_results:
                content = f"快捷搜索 - 作者：{author.mention}：\n\n❌ **搜索出错：** {initial_results['error']}"
            else:
                content = f"快捷搜索 - 作者：{author.mention}：\n\n🔍 **搜索结果：** 该作者暂无帖子"
            
            # 更新view状态
            view._last_content = content
            view._last_embeds = []
            view._has_results = False
            
            await interaction.followup.send(content, view=view, ephemeral=True)
        else:
            # 有搜索结果时，创建合并视图
            results_view = SearchResultsView(
                view.search_cog, view.user_id,
                [], [], "",  # 初始搜索为空条件（只限制作者）
                view.channel_ids,
                [author.id], None,  # 强制只看指定作者
                None, None,  # 忽略时间偏好
                1, initial_results['per_page'], initial_results['total'],
                view.sort_method, view.sort_order, "and"  # 固定标签逻辑
            )
            
            # 合并两个view的按钮
            combined_view = CombinedSearchView(view, results_view)
            
            content = f"快捷搜索 - 作者：{author.mention}：\n\n🔍 **搜索结果：** 找到 {initial_results['total']} 个帖子 (第1/{results_view.max_page}页)"
            
            # 保存状态
            view._last_content = content
            view._last_embeds = initial_results['embeds']
            view._has_results = True
            
            await interaction.followup.send(content, view=combined_view, embeds=initial_results['embeds'], ephemeral=True)

    # ----- Embed 构造 -----
    def _build_thread_embed(self, thread_row: dict, guild: discord.Guild, preview_mode: str = "thumbnail"):
        thread_id = thread_row['thread_id']
        title = thread_row['title']
        original_poster_id = thread_row['author_id']
        created_time = datetime.datetime.fromisoformat(thread_row['created_at'])
        last_active_time = datetime.datetime.fromisoformat(thread_row['last_active_at'])
        reaction_count = thread_row['reaction_count']
        reply_count = thread_row['reply_count']
        tags_str = thread_row.get('tags', '') or ''
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        first_message_excerpt = thread_row['first_message_excerpt'] or ''
        attachment_url = thread_row['thumbnail_url']

        embed = discord.Embed(title=title, description=f"作者 <@{original_poster_id}>")
        
        # 基础统计信息
        basic_stats = (
            f"发帖日期: **{created_time.strftime('%Y-%m-%d %H:%M:%S')}** | "
            f"最近活跃: **{last_active_time.strftime('%Y-%m-%d %H:%M:%S')}**\n"
            f"最高反应数: **{reaction_count}** | 总回复数: **{reply_count}**\n"
            f"标签: **{', '.join(tags) if tags else '无'}**"
        )
        
        embed.add_field(
            name="统计",
            value=basic_stats,
            inline=False,
        )
        
        excerpt_display = first_message_excerpt[:200] + "..." if len(first_message_excerpt) > 200 else (first_message_excerpt or "无内容")
        embed.add_field(name="首楼摘要", value=excerpt_display, inline=False)
        
        # 根据用户偏好设置预览图显示方式
        if attachment_url:
            if preview_mode == "image":
                embed.set_image(url=attachment_url)
            else:  # thumbnail
                embed.set_thumbnail(url=attachment_url)
        
        embed.url = f"https://discord.com/channels/{guild.id}/{thread_id}"
        return embed

# 添加async setup的cog加载时注册持久化View
async def setup(bot):
    await bot.add_cog(Search(bot))