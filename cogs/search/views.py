import discord
import math
import re
import asyncio
import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import Search

import database

# ----- 持久化搜索按钮 -----
class PersistentChannelSearchView(discord.ui.View):
    def __init__(self, channel_id: int, thread_id: int = None):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.thread_id = thread_id

    @discord.ui.button(label="🔍 搜索本频道", style=discord.ButtonStyle.primary, custom_id="persistent_channel_search")
    async def search_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 从按钮所在的消息中获取embed，从embed中提取channel_id
        if interaction.message.embeds:
            embed = interaction.message.embeds[0]
            # 从description中提取channel_id
            import re
            match = re.search(r'<#(\d+)>', embed.description or "")
            if match:
                channel_id = int(match.group(1))
            else:
                # 如果无法从embed中提取，使用默认值
                channel_id = self.channel_id
        else:
            channel_id = self.channel_id
            
        # 创建标签选择视图并执行初始搜索
        view = TagSelectionView(channel_id)
        initial_results = await view.setup_with_initial_search(interaction.guild, interaction.user.id)
        
        mode_text = f"标签匹配: {'全部' if view.tag_logic == 'and' else '任一'}"
        
        if not initial_results['has_results']:
            # 没有搜索结果时
            if 'error' in initial_results:
                content = f"选择搜索条件 - {mode_text}：\n\n❌ **搜索出错：** {initial_results['error']}"
            else:
                content = f"选择搜索条件 - {mode_text}：\n\n🔍 **搜索结果：** 未找到符合条件的帖子"
            
            # 更新view状态
            view._last_content = content
            view._last_embeds = []
            view._has_results = False
            
            await interaction.response.send_message(content, view=view, ephemeral=True)
            
        else:
            # 有搜索结果时，创建合并视图
            results_view = SearchResultsView(
                view.search_cog, view.user_id,
                [], [], "",  # 初始搜索为空条件
                view.channel_ids, 
                initial_results['prefs']['include_authors'] if initial_results['prefs']['include_authors'] else None,
                initial_results['prefs']['exclude_authors'] if initial_results['prefs']['exclude_authors'] else None,
                initial_results['prefs']['after_date'], initial_results['prefs']['before_date'],
                1, initial_results['per_page'], initial_results['total'], 
                view.sort_method, view.sort_order, initial_results['prefs']['tag_logic']
            )
            
            # 合并两个view的按钮
            combined_view = CombinedSearchView(view, results_view)
            
            content = f"选择搜索条件 - {mode_text}：\n\n🔍 **搜索结果：** 找到 {initial_results['total']} 个帖子 (第1/{results_view.max_page}页)"
            
            # 保存状态
            view._last_content = content
            view._last_embeds = initial_results['embeds']
            view._has_results = True
            
            await interaction.response.send_message(content, view=combined_view, embeds=initial_results['embeds'], ephemeral=True)

class PersistentGlobalSearchView(discord.ui.View):
    def __init__(self, message_id: str = None):
        super().__init__(timeout=None)
        self.message_id = message_id

    async def start_search_flow(self, interaction: discord.Interaction):
        """启动全局搜索流程的通用逻辑"""
        # 获取所有论坛频道
        all_forum_channels = [ch for ch in interaction.guild.channels if isinstance(ch, discord.ForumChannel)]
        
        # 从TagSystem获取已索引的频道ID（使用缓存）
        tag_system = interaction.client.get_cog("TagSystem")
        if tag_system and hasattr(tag_system, 'indexed_channel_ids'):
            indexed_channel_ids = tag_system.indexed_channel_ids
        else:
            # 如果TagSystem不可用，回退到数据库查询
            try:
                indexed_channel_ids = set(await database.get_indexed_channel_ids())
            except Exception as e:
                await interaction.response.send_message(f"❌ 查询索引频道时出错: {e}", ephemeral=True)
                return
        
        # 只保留已索引的论坛频道
        forum_channels = [ch for ch in all_forum_channels if ch.id in indexed_channel_ids]
        
        if not forum_channels:
            await interaction.response.send_message("暂无已索引的论坛频道。请先使用 `/构建索引` 命令对频道进行索引。", ephemeral=True)
            return
        
        view = ChannelSelectionView(forum_channels)
        await interaction.response.send_message("选择要搜索的频道：", view=view, ephemeral=True)

    @discord.ui.button(label="🌐 选择频道搜索", style=discord.ButtonStyle.success, custom_id="persistent_global_search")
    async def search_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """按钮回调，调用通用的搜索流程方法"""
        await self.start_search_flow(interaction)

class ChannelSelectionView(discord.ui.View):
    def __init__(self, channels: list[discord.ForumChannel]):
        super().__init__(timeout=900)  # 15分钟
        self.channels = channels  # 保存频道列表
        self._last_interaction = None
        self.selected_channels = []  # 保存选中的频道
        
        # 如果频道太多，分批处理
        options = []
        
        # 添加"全部频道"选项在最上面
        options.append(discord.SelectOption(
            label="全部频道",
            value="all_channels",
            description="搜索所有已索引的论坛频道"
        ))
        
        for channel in channels[:24]:  # Discord限制25个选项，所以只取24个
            options.append(discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"ID: {channel.id}"
            ))
        
        self.channel_select = discord.ui.Select(
            placeholder="选择论坛频道（可多选）...",
            options=options,
            min_values=1,
            max_values=min(len(options), 25)  # 允许多选，最多25个
        )
        self.channel_select.callback = self.channel_selected
        self.add_item(self.channel_select)
        
        # 添加确定按钮
        self.confirm_button = discord.ui.Button(
            label="✅ 确定搜索",
            style=discord.ButtonStyle.success,
            disabled=True  # 初始状态为禁用
        )
        self.confirm_button.callback = self.confirm_selection
        self.add_item(self.confirm_button)

    async def channel_selected(self, interaction: discord.Interaction):
        self._last_interaction = interaction
        
        # 处理选择逻辑
        if "all_channels" in self.channel_select.values:
            # 如果选择了"全部频道"，使用所有频道
            self.selected_channels = [ch.id for ch in self.channels]
            selected_names = ["全部频道"]
        else:
            # 选择了具体频道
            self.selected_channels = [int(ch_id) for ch_id in self.channel_select.values]
            selected_names = [ch.name for ch in self.channels if ch.id in self.selected_channels]
        
        # 启用确定按钮
        self.confirm_button.disabled = False
        
        # 更新消息显示当前选择
        selected_text = ", ".join(selected_names)
        content = f"选择要搜索的频道（可多选）：\n\n**已选择：** {selected_text}\n\n点击【确定搜索】按钮继续"
        
        await interaction.response.edit_message(content=content, view=self)

    async def confirm_selection(self, interaction: discord.Interaction):
        self._last_interaction = interaction
        
        if not self.selected_channels:
            await interaction.response.send_message("请先选择要搜索的频道。", ephemeral=True)
            return
        
        # 创建标签选择视图并执行初始搜索
        view = TagSelectionView(self.selected_channels)
        initial_results = await view.setup_with_initial_search(interaction.guild, interaction.user.id)
        
        # 显示选择的频道信息
        if len(self.selected_channels) == len(self.channels):
            channel_info = "全部频道"
        else:
            selected_names = [ch.name for ch in self.channels if ch.id in self.selected_channels]
            channel_info = ", ".join(selected_names)
        
        mode_text = f"标签匹配: {'全部' if view.tag_logic == 'and' else '任一'}"
        
        if not initial_results['has_results']:
            # 没有搜索结果时
            if 'error' in initial_results:
                content = f"选择搜索条件 - {mode_text}：\n\n**搜索范围：** {channel_info}\n\n❌ **搜索出错：** {initial_results['error']}"
            else:
                content = f"选择搜索条件 - {mode_text}：\n\n**搜索范围：** {channel_info}\n\n🔍 **搜索结果：** 未找到符合条件的帖子"
            
            # 更新view状态
            view._last_content = content
            view._last_embeds = []
            view._has_results = False
            
            await interaction.response.edit_message(content=content, view=view, embeds=[])
        else:
            # 有搜索结果时，创建合并视图
            results_view = SearchResultsView(
                view.search_cog, view.user_id,
                [], [], "",  # 初始搜索为空条件
                view.channel_ids, 
                initial_results['prefs']['include_authors'] if initial_results['prefs']['include_authors'] else None,
                initial_results['prefs']['exclude_authors'] if initial_results['prefs']['exclude_authors'] else None,
                initial_results['prefs']['after_date'], initial_results['prefs']['before_date'],
                1, initial_results['per_page'], initial_results['total'], 
                view.sort_method, view.sort_order, initial_results['prefs']['tag_logic']
            )
            
            # 合并两个view的按钮
            combined_view = CombinedSearchView(view, results_view)
            
            content = f"选择搜索条件 - {mode_text}：\n\n**搜索范围：** {channel_info}\n\n🔍 **搜索结果：** 找到 {initial_results['total']} 个帖子 (第1/{results_view.max_page}页)"
            
            # 保存状态
            view._last_content = content
            view._last_embeds = initial_results['embeds']
            view._has_results = True
            
            await interaction.response.edit_message(content=content, view=combined_view, embeds=initial_results['embeds'])
    
    async def on_timeout(self):
        """超时处理"""
        try:
            # 创建状态字典
            view_state = {
                'view_type': 'ChannelSelectionView'
            }
            
            # 创建超时视图
            timeout_view = TimeoutView(view_state)
            
            # 更新消息
            if self._last_interaction:
                await self._last_interaction.edit_original_response(
                    content="⏰ 频道选择界面已超时（15分钟），点击继续按钮重新选择",
                    view=timeout_view,
                    embeds=[]
                )
        except Exception:
            # 如果更新失败，静默处理
            pass

# ----- 标签选择界面 -----
class TagSelectionView(discord.ui.View):
    def __init__(self, channel_ids):
        super().__init__(timeout=900)  # 15分钟
        # 支持单个频道ID或频道ID列表
        if isinstance(channel_ids, int):
            self.channel_ids = [channel_ids]
        elif isinstance(channel_ids, list):
            self.channel_ids = channel_ids
        else:
            raise ValueError("channel_ids must be int or list of int")
        
        # 为了向后兼容，保留channel_id属性
        self.channel_id = self.channel_ids[0] if len(self.channel_ids) == 1 else None
        
        self.include_tags = set()
        self.exclude_tags = set()
        self.include_keywords = []
        self.exclude_keywords = []
        self.tag_logic = "and"  # 'and' 或 'or'
        self.search_cog: "Search" = None  # 将在setup中设置
        self.user_id = None  # 将在setup中设置
        self.sort_method = "comprehensive"  # 默认使用综合排序
        self.sort_order = "desc"  # 默认降序排序
        self.tag_page = 0  # 当前标签页
        self.tags_per_page = 25  # 每页显示的标签数 (Select菜单最多25个)
        self.all_tags = []  # 所有标签列表
        self._last_interaction = None  # 保存最后一次交互
        self._last_content = None  # 保存最后的内容
        self._last_embeds = None  # 保存最后的embeds
        self._has_results = False  # 是否有搜索结果
        
    async def setup(self, guild: discord.Guild, user_id: int = None):
        """获取标签并设置UI"""
        self.user_id = user_id
        
        # 尝试获取Search cog来使用缓存的tags
        search_cog = None
        try:
            # 通过guild.me获取bot实例
            if hasattr(guild, 'me') and guild.me:
                bot = guild.me._state._get_client()
                search_cog = bot.get_cog("Search")
                self.search_cog = search_cog
        except:
            pass
        
        if search_cog and hasattr(search_cog, 'get_merged_tags'):
            # 使用缓存的tags
            self.all_tags = search_cog.get_merged_tags(self.channel_ids)
        else:
            # fallback: 直接从Discord频道获取标签并合并重名tag
            all_tags_names = set()
            for channel_id in self.channel_ids:
                channel = guild.get_channel(channel_id)
                if isinstance(channel, discord.ForumChannel):
                    for tag in channel.available_tags:
                        all_tags_names.add(tag.name)
            
            # 合并重名tag，只保留tag名称
            self.all_tags = [(0, tag_name) for tag_name in sorted(all_tags_names)]
        
        # 清空现有items
        self.clear_items()
        
        # 计算当前页的标签
        start_idx = self.tag_page * self.tags_per_page
        end_idx = start_idx + self.tags_per_page
        current_page_tags = self.all_tags[start_idx:end_idx]
        
        # 第 0 行: 正选标签
        include_options = [discord.SelectOption(label=tag_name, value=tag_name) for _, tag_name in current_page_tags]
        self.add_item(IncludeTagSelect(include_options, list(self.include_tags)))

        # 第 1 行: 反选标签
        exclude_options = [discord.SelectOption(label=tag_name, value=tag_name) for _, tag_name in current_page_tags]
        self.add_item(ExcludeTagSelect(exclude_options, list(self.exclude_tags)))
        
        # 第 2 行: 控制按钮
        keyword_button = KeywordButton()
        keyword_button.row = 2
        self.add_item(keyword_button)

        if len(self.all_tags) > self.tags_per_page:
            prev_page_button = TagPageButton("◀️ 上一页", "prev")
            self.add_item(prev_page_button)

        tag_logic_button = TagLogicButton(self.tag_logic)
        tag_logic_button.row = 2
        self.add_item(tag_logic_button)

        if len(self.all_tags) > self.tags_per_page:
            next_page_button = TagPageButton("▶️ 下一页", "next")
            self.add_item(next_page_button)
            
        sort_order_button = SortOrderButton(self.sort_order)
        sort_order_button.row = 2
        self.add_item(sort_order_button)
        
        # 第 3 行: 排序选择器
        sort_select = SortMethodSelect(self.sort_method)
        sort_select.row = 3
        self.add_item(sort_select)

    async def setup_with_initial_search(self, guild: discord.Guild, user_id: int = None):
        """获取标签并设置UI，同时执行初始搜索"""
        # 先执行普通setup
        await self.setup(guild, user_id)
        
        # 执行初始搜索并返回结果
        return await self.get_initial_search_results(guild)

    async def get_initial_search_results(self, guild: discord.Guild):
        """获取初始搜索结果（显示所有帖子，应用用户偏好）"""
        try:
            # 获取用户搜索偏好
            prefs = await database.get_user_search_preferences(self.user_id)
            
            # 初始搜索：空标签，空关键词（显示所有帖子）
            include_tags = []
            exclude_tags = []
            include_keywords = ""
            
            per_page = await database.get_results_per_page(self.user_id)
            
            # 应用用户偏好
            include_authors = prefs['include_authors'] if prefs['include_authors'] else None
            exclude_authors = prefs['exclude_authors'] if prefs['exclude_authors'] else None
            after_ts = prefs['after_date']
            before_ts = prefs['before_date']
            
            total = await database.count_threads_for_search(
                include_tags, exclude_tags, include_keywords, 
                self.channel_ids, include_authors, exclude_authors, after_ts, before_ts,
                prefs['tag_logic']
            )
            
            if total == 0:
                # 没有结果时只返回基本信息
                return {
                    'total': 0,
                    'threads': [],
                    'embeds': [],
                    'has_results': False
                }
            
            threads = await database.search_threads(
                include_tags, exclude_tags, include_keywords,
                self.channel_ids, include_authors, exclude_authors, after_ts, before_ts,
                0, per_page, self.sort_method, self.sort_order, prefs['tag_logic']
            )
            
            # 获取搜索cog来构建embed
            if not self.search_cog:
                # 通过guild.me获取bot实例
                if hasattr(guild, 'me') and guild.me:
                    bot = guild.me._state._get_client()
                    self.search_cog = bot.get_cog("Search")
                    
            # 如果缓存已失效，重新缓存标签
            if self.search_cog and hasattr(self.search_cog, 'cache_channel_tags'):
                # 检查是否需要更新缓存
                if not self.search_cog.channel_tags_cache:
                    await self.search_cog.cache_channel_tags()
                    
            embeds = [self.search_cog._build_thread_embed(t, guild, prefs.get('preview_image_mode', 'thumbnail')) for t in threads]
            
            return {
                'total': total,
                'threads': threads,
                'embeds': embeds,
                'has_results': True,
                'per_page': per_page,
                'prefs': prefs
            }
            
        except Exception as e:
            print(f"初始搜索出错: {e}")
            return {
                'total': 0,
                'threads': [],
                'embeds': [],
                'has_results': False,
                'error': str(e)
            }

    def _build_content_string(self, total: int, current_page: int = 1, max_page: int = 1) -> str:
        """构建统一的消息内容字符串"""
        
        # 基础标题
        if isinstance(self, AuthorTagSelectionView):
            title = f"快捷搜索 - 作者：<@{self.author_id}>"
        else:
            title = "选择搜索条件"

        # 筛选条件文本
        filters = []
        if self.include_tags:
            filters.append(f"**正选**: {', '.join(self.include_tags)}")
        if self.exclude_tags:
            filters.append(f"**反选**: {', '.join(self.exclude_tags)}")
        if self.include_keywords:
            filters.append(f"**关键词**: {', '.join(self.include_keywords)}")
        
        filter_text = " | ".join(filters) if filters else "无"

        # 结果文本
        if total > 0:
            result_text = f"🔍 **搜索结果：** 找到 {total} 个帖子 (第{current_page}/{max_page}页)"
        else:
            result_text = "🔍 **搜索结果：** 未找到符合条件的帖子"

        return f"{title}\n**筛选条件**: {filter_text}\n\n{result_text}"

    async def update_search_results(self, interaction: discord.Interaction, *, edit_original: bool = True):
        """更新搜索结果"""
        try:
            # 保存交互状态
            self._last_interaction = interaction
            
            # 重新构建UI以更新占位符等状态
            await self.setup(interaction.guild, self.user_id)
            
            # 获取用户搜索偏好
            prefs = await database.get_user_search_preferences(self.user_id)
            
            include_tags = list(self.include_tags)
            exclude_tags = list(self.exclude_tags)
            
            # 处理关键词
            keywords_parts = []
            if self.include_keywords:
                keywords_parts.append(" ".join(self.include_keywords))
            
            include_keywords = " ".join(keywords_parts) if keywords_parts else ""
            
            per_page = await database.get_results_per_page(self.user_id)
            
            # 应用用户偏好
            include_authors = prefs['include_authors'] if prefs['include_authors'] else None
            exclude_authors = prefs['exclude_authors'] if prefs['exclude_authors'] else None
            after_ts = prefs['after_date']
            before_ts = prefs['before_date']
            
            # 如果是作者快捷搜索，强制覆盖作者偏好
            if isinstance(self, AuthorTagSelectionView):
                include_authors = [self.author_id]
                exclude_authors = None
                after_ts = None
                before_ts = None
            
            total = await database.count_threads_for_search(
                include_tags, exclude_tags, include_keywords,
                self.channel_ids, include_authors, exclude_authors, after_ts, before_ts,
                self.tag_logic
            )
            
            if total == 0:
                # 没有结果时只更新标签选择界面
                content = self._build_content_string(total=0)
                self._last_content = content
                self._last_embeds = []
                self._has_results = False
                
                # 使用 self (TagSelectionView)
                view_to_send = self
                
                if edit_original:
                    await interaction.response.edit_message(content=content, view=view_to_send, embeds=[])
                else:
                    await interaction.edit_original_response(content=content, view=view_to_send, embeds=[])
                return
            
            threads = await database.search_threads(
                include_tags, exclude_tags, include_keywords,
                self.channel_ids, include_authors, exclude_authors, after_ts, before_ts,
                0, per_page, self.sort_method, self.sort_order, self.tag_logic
            )
            
            # 获取搜索cog来构建embed
            if not self.search_cog:
                self.search_cog = interaction.client.get_cog("Search")
                
            # 如果缓存已失效，重新缓存标签
            if self.search_cog and hasattr(self.search_cog, 'cache_channel_tags'):
                if not self.search_cog.channel_tags_cache:
                    await self.search_cog.cache_channel_tags()
                
            embeds = [self.search_cog._build_thread_embed(t, interaction.guild, prefs.get('preview_image_mode', 'thumbnail')) for t in threads]
            
            # 创建搜索结果view
            results_view = SearchResultsView(
                self.search_cog, self.user_id,
                include_tags, exclude_tags, include_keywords,
                self.channel_ids, include_authors, exclude_authors, after_ts, before_ts,
                1, per_page, total, self.sort_method, self.sort_order, self.tag_logic
            )
            
            # 合并两个view的按钮
            combined_view = CombinedSearchView(self, results_view)
            
            content = self._build_content_string(total, 1, results_view.max_page)
            
            # 保存状态
            self._last_content = content
            self._last_embeds = embeds
            self._has_results = True
            
            if edit_original:
                await interaction.response.edit_message(content=content, view=combined_view, embeds=embeds)
            else:
                await interaction.edit_original_response(content=content, view=combined_view, embeds=embeds)
            
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"搜索出错: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"搜索出错: {e}", ephemeral=True)
    
    async def on_timeout(self):
        """超时处理"""
        try:
            # 创建状态字典
            view_state = {
                'view_type': 'TagSelectionView',
                'channel_ids': self.channel_ids,
                'include_tags': list(self.include_tags),
                'exclude_tags': list(self.exclude_tags),
                'include_keywords': self.include_keywords,
                'exclude_keywords': self.exclude_keywords,
                'tag_logic': self.tag_logic,
                'sort_method': self.sort_method,
                'sort_order': self.sort_order,
                'tag_page': self.tag_page,
                'all_tags': self.all_tags,
                'user_id': self.user_id,
                'has_results': self._has_results
            }
            
            # 创建超时视图
            timeout_view = TimeoutView(view_state)
            
            # 更新消息
            if self._last_interaction:
                await self._last_interaction.edit_original_response(
                    content="⏰ 搜索界面已超时（15分钟），点击继续按钮恢复搜索状态",
                    view=timeout_view,
                    embeds=[]
                )
        except Exception:
            # 如果更新失败，静默处理
            pass

class IncludeTagSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption], current_values: list[str]):
        if current_values:
            placeholder_text = "已选正选: " + ", ".join(current_values)
            if len(placeholder_text) > 100: # Discord 占位符长度限制
                placeholder_text = placeholder_text[:97] + "..."
        else:
            placeholder_text = "选择要包含的标签 (正选)"

        super().__init__(
            placeholder=placeholder_text,
            min_values=0,
            max_values=len(options) if options else 1, # max_values不能为0
            options=options if options else [discord.SelectOption(label="无可用标签", value="no_tags_placeholder", default=True)],
            row=0,
            disabled=not options
        )
        # 设置当前选中的值
        for option in self.options:
            if option.value in current_values:
                option.default = True

    async def callback(self, interaction: discord.Interaction):
        tag_view = self.view.tag_view if hasattr(self.view, 'tag_view') else self.view
        
        # 获取当前页所有可见的标签
        current_page_options = {opt.value for opt in self.options if opt.value != "no_tags_placeholder"}
        
        # 计算在其他页面上已选的标签
        tags_selected_on_other_pages = tag_view.include_tags - current_page_options
        
        # 获取当前页选中的标签
        selected_on_this_page = set(self.values)
        selected_on_this_page.discard("no_tags_placeholder")
        
        # 新的总选择 = 其他页面的选择 + 当前页面的选择
        tag_view.include_tags = tags_selected_on_other_pages.union(selected_on_this_page)
        
        await tag_view.update_search_results(interaction, edit_original=True)

class ExcludeTagSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption], current_values: list[str]):
        if current_values:
            placeholder_text = "已选反选: " + ", ".join(current_values)
            if len(placeholder_text) > 100: # Discord 占位符长度限制
                placeholder_text = placeholder_text[:97] + "..."
        else:
            placeholder_text = "选择要排除的标签 (反选)"

        super().__init__(
            placeholder=placeholder_text,
            min_values=0,
            max_values=len(options) if options else 1,
            options=options if options else [discord.SelectOption(label="无可用标签", value="no_tags_placeholder", default=True)],
            row=1,
            disabled=not options
        )
        # 设置当前选中的值
        for option in self.options:
            if option.value in current_values:
                option.default = True

    async def callback(self, interaction: discord.Interaction):
        tag_view = self.view.tag_view if hasattr(self.view, 'tag_view') else self.view
        
        # 获取当前页所有可见的标签
        current_page_options = {opt.value for opt in self.options if opt.value != "no_tags_placeholder"}
        
        # 计算在其他页面上已选的标签
        tags_selected_on_other_pages = tag_view.exclude_tags - current_page_options
        
        # 获取当前页选中的标签
        selected_on_this_page = set(self.values)
        selected_on_this_page.discard("no_tags_placeholder")
        
        # 新的总选择 = 其他页面的选择 + 当前页面的选择
        tag_view.exclude_tags = tags_selected_on_other_pages.union(selected_on_this_page)
        
        await tag_view.update_search_results(interaction, edit_original=True)

class TagLogicButton(discord.ui.Button):
    def __init__(self, current_logic: str):
        self.current_logic = current_logic
        label = "匹配: 同时" if current_logic == "and" else "匹配: 任一"
        style = discord.ButtonStyle.primary if current_logic == "and" else discord.ButtonStyle.secondary
        super().__init__(label=label, style=style, row=2)

    async def callback(self, interaction: discord.Interaction):
        tag_view = self.view.tag_view if hasattr(self.view, 'tag_view') else self.view
        tag_view.tag_logic = "or" if tag_view.tag_logic == "and" else "and"
        
        # 更新自身状态
        self.label = "匹配: 全部" if tag_view.tag_logic == "and" else "匹配: 任一"
        self.style = discord.ButtonStyle.primary if tag_view.tag_logic == "and" else discord.ButtonStyle.secondary
        
        await tag_view.update_search_results(interaction, edit_original=True)

class TagPageButton(discord.ui.Button):
    def __init__(self, label: str, action: str):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=2)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        tag_view = self.view.tag_view if hasattr(self.view, 'tag_view') else self.view
        
        tag_view._last_interaction = interaction
        
        max_page = (len(tag_view.all_tags) - 1) // tag_view.tags_per_page
        
        if self.action == "prev":
            tag_view.tag_page = max(0, tag_view.tag_page - 1)
        elif self.action == "next":
            tag_view.tag_page = min(max_page, tag_view.tag_page + 1)
        
        # 重新设置UI，这会创建新的Select菜单
        await tag_view.setup(interaction.guild, tag_view.user_id)
        
        # 翻页后，需要重新渲染整个视图，包括可能存在的搜索结果
        await tag_view.update_search_results(interaction, edit_original=True)

class SortMethodSelect(discord.ui.Select):
    def __init__(self, current_sort: str):
        options = [
            discord.SelectOption(
                label="🧠 综合排序",
                value="comprehensive",
                description="智能混合权重算法（时间+标签+反应）",
                default=(current_sort == "comprehensive")
            ),
            discord.SelectOption(
                label="🕐 按发帖时间",
                value="created_time", 
                description="按帖子创建时间倒序排列",
                default=(current_sort == "created_time")
            ),
            discord.SelectOption(
                label="⏰ 按活跃时间",
                value="active_time",
                description="按最近活跃时间倒序排列", 
                default=(current_sort == "active_time")
            ),
            discord.SelectOption(
                label="🎉 按反应数",
                value="reaction_count",
                description="按最高反应数倒序排列",
                default=(current_sort == "reaction_count")
            )
        ]
        super().__init__(placeholder="选择排序方式...", options=options, row=3)

    async def callback(self, interaction: discord.Interaction):
        # 检查当前view是CombinedSearchView还是TagSelectionView
        if hasattr(self.view, 'tag_view'):
            # 在CombinedSearchView中
            tag_view = self.view.tag_view
        else:
            # 在TagSelectionView中
            tag_view = self.view
        
        # 保存交互状态
        tag_view._last_interaction = interaction
        
        tag_view.sort_method = self.values[0]
        
        # 更新选择器的选中状态
        for option in self.options:
            option.default = (option.value == self.values[0])
        
        # 立即更新搜索结果
        await tag_view.update_search_results(interaction, edit_original=True)

class SortOrderButton(discord.ui.Button):
    def __init__(self, sort_order: str):
        label = "📉 降序" if sort_order == "desc" else "📈 升序"
        super().__init__(label=label, style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        # 检查当前view是CombinedSearchView还是TagSelectionView
        if hasattr(self.view, 'tag_view'):
            # 在CombinedSearchView中
            tag_view = self.view.tag_view
        else:
            # 在TagSelectionView中
            tag_view = self.view
        
        # 保存交互状态
        tag_view._last_interaction = interaction
        
        # 切换排序方向
        tag_view.sort_order = "asc" if tag_view.sort_order == "desc" else "desc"
        
        # 更新按钮标签
        self.label = "📉 降序" if tag_view.sort_order == "desc" else "📈 升序"
        
        # 立即更新搜索结果
        await tag_view.update_search_results(interaction, edit_original=True)

class KeywordButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="📝 关键词", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        # 检查当前view是CombinedSearchView还是TagSelectionView
        if hasattr(self.view, 'tag_view'):
            # 在CombinedSearchView中
            tag_view = self.view.tag_view
        else:
            # 在TagSelectionView中
            tag_view = self.view
        
        # 保存交互状态
        tag_view._last_interaction = interaction
        
        await interaction.response.send_modal(KeywordModal(tag_view))

class KeywordModal(discord.ui.Modal, title="设置关键词过滤"):
    def __init__(self, parent_view: TagSelectionView):
        super().__init__()
        self.parent_view = parent_view
        
        self.include_input = discord.ui.TextInput(
            label="包含关键词（逗号或斜杠分隔）",
            placeholder="在标题或首楼中必须包含的关键词",
            required=False,
            default=", ".join(self.parent_view.include_keywords)
        )
        self.exclude_input = discord.ui.TextInput(
            label="排除关键词 (逗号分隔)", 
            placeholder="在标题或首楼中不能包含的关键词",
            required=False,
            default=", ".join(self.parent_view.exclude_keywords)
        )
        self.add_item(self.include_input)
        self.add_item(self.exclude_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 保存交互状态
        self.parent_view._last_interaction = interaction
        
        self.parent_view.include_keywords = [k.strip() for k in self.include_input.value.split(',') if k.strip()]
        self.parent_view.exclude_keywords = [k.strip() for k in self.exclude_input.value.split(',') if k.strip()]
        
        # 关键词更新后立即更新搜索结果
        await self.parent_view.update_search_results(interaction, edit_original=True)

# ----- 搜索结果分页 -----
class SearchResultsView(discord.ui.View):
    def __init__(self, cog: "Search", user_id: int, include_tags, exclude_tags, keywords, channel_ids, include_authors, exclude_authors, after_ts, before_ts, current_page, per_page, total, sort_method: str = "comprehensive", sort_order: str = "desc", tag_logic: str = "and"):
        super().__init__(timeout=900)  # 15分钟
        self.cog = cog
        self.user_id = user_id
        self.include_tags = include_tags
        self.exclude_tags = exclude_tags
        self.keywords = keywords
        self.channel_ids = channel_ids
        self.include_authors = include_authors
        self.exclude_authors = exclude_authors
        self.after_ts = after_ts
        self.before_ts = before_ts
        self.per_page = per_page
        self.total = total
        self.max_page = max(1, math.ceil(total / per_page))
        self.current_page = current_page
        self.sort_method = sort_method
        self.sort_order = sort_order
        self.tag_logic = tag_logic
        self._last_interaction = None  # 保存最后一次交互
        
        # 添加分页按钮
        self.add_item(PageButton("⏮️", "first"))
        self.add_item(PageButton("◀️", "prev"))
        self.add_item(CurrentPageButton(self.current_page, self.max_page))
        self.add_item(PageButton("▶️", "next"))
        self.add_item(PageButton("⏭️", "last"))

    async def go_to_page(self, interaction: discord.Interaction, target_page: int):
        if target_page < 1 or target_page > self.max_page:
            await interaction.response.send_message("页码超出范围。", ephemeral=True)
            return
        
        # 保存交互状态
        self._last_interaction = interaction
        
        await interaction.response.defer()
        
        offset = (target_page - 1) * self.per_page
        threads = await database.search_threads(
            self.include_tags, self.exclude_tags, self.keywords,
            self.channel_ids, self.include_authors, self.exclude_authors, self.after_ts, self.before_ts,
            offset, self.per_page, self.sort_method, self.sort_order, self.tag_logic
        )
        
        # 获取用户预览图偏好设置
        prefs = await database.get_user_search_preferences(self.user_id)
        embeds = [self.cog._build_thread_embed(t, interaction.guild, prefs.get('preview_image_mode', 'thumbnail')) for t in threads]
        self.current_page = target_page
        
        # 更新当前页按钮
        for item in self.children:
            if isinstance(item, CurrentPageButton):
                item.label = f"{self.current_page}/{self.max_page}"
        
        await interaction.edit_original_response(embeds=embeds, view=self)
    
    async def on_timeout(self):
        """超时处理"""
        try:
            # 创建状态字典
            view_state = {
                'view_type': 'SearchResultsView',
                'user_id': self.user_id,
                'include_tags': self.include_tags,
                'exclude_tags': self.exclude_tags,
                'keywords': self.keywords,
                'channel_ids': self.channel_ids,
                'include_authors': self.include_authors,
                'exclude_authors': self.exclude_authors,
                'after_ts': self.after_ts,
                'before_ts': self.before_ts,
                'current_page': self.current_page,
                'per_page': self.per_page,
                'total': self.total,
                'sort_method': self.sort_method,
                'sort_order': self.sort_order,
                'tag_logic': self.tag_logic
            }
            
            # 创建超时视图
            timeout_view = TimeoutView(view_state)
            
            # 更新消息
            if self._last_interaction:
                await self._last_interaction.edit_original_response(
                    content="⏰ 搜索结果界面已超时（15分钟），点击继续按钮恢复搜索状态",
                    view=timeout_view,
                    embeds=[]
                )
        except Exception:
            # 如果更新失败，静默处理
            pass

class PageButton(discord.ui.Button):
    def __init__(self, label: str, action: str):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        # 检查当前view是CombinedSearchView还是SearchResultsView
        if hasattr(self.view, 'results_view'):
            # 在CombinedSearchView中
            results_view = self.view.results_view
            # 保存交互状态
            results_view._last_interaction = interaction
            if hasattr(self.view, 'tag_view'):
                self.view.tag_view._last_interaction = interaction
        else:
            # 在独立的SearchResultsView中
            results_view = self.view
            # 保存交互状态
            results_view._last_interaction = interaction
            
        page = results_view.current_page
        
        if self.action == "first":
            page = 1
        elif self.action == "prev":
            page = max(1, results_view.current_page - 1)
        elif self.action == "next":
            page = min(results_view.max_page, results_view.current_page + 1)
        elif self.action == "last":
            page = results_view.max_page
        
        await self.go_to_page_combined(interaction, page, results_view)
    
    async def go_to_page_combined(self, interaction: discord.Interaction, target_page: int, results_view):
        if target_page < 1 or target_page > results_view.max_page:
            await interaction.response.send_message("页码超出范围。", ephemeral=True)
            return
        
        # 保存交互状态
        results_view._last_interaction = interaction
        if hasattr(self.view, 'tag_view'):
            self.view.tag_view._last_interaction = interaction
        
        await interaction.response.defer()
        
        offset = (target_page - 1) * results_view.per_page
        threads = await database.search_threads(
            results_view.include_tags, results_view.exclude_tags, results_view.keywords,
            results_view.channel_ids, results_view.include_authors, results_view.exclude_authors, 
            results_view.after_ts, results_view.before_ts,
            offset, results_view.per_page, results_view.sort_method, results_view.sort_order,
            results_view.tag_logic
        )
        
        # 获取用户预览图偏好设置
        prefs = await database.get_user_search_preferences(results_view.user_id)
        embeds = [results_view.cog._build_thread_embed(t, interaction.guild, prefs.get('preview_image_mode', 'thumbnail')) for t in threads]
        results_view.current_page = target_page
        
        # 更新当前页按钮
        for item in self.view.children:
            if isinstance(item, CurrentPageButton):
                item.label = f"{results_view.current_page}/{results_view.max_page}"
        
        # 如果在CombinedSearchView中，更新内容
        if hasattr(self.view, 'tag_view'):
            tag_view = self.view.tag_view
            content = tag_view._build_content_string(results_view.total, results_view.current_page, results_view.max_page)
            
            # 保存CombinedSearchView的状态
            tag_view._last_content = content
            tag_view._last_embeds = embeds
            
            await interaction.edit_original_response(content=content, embeds=embeds, view=self.view)
        else:
            await interaction.edit_original_response(embeds=embeds, view=self.view)

class CurrentPageButton(discord.ui.Button):
    def __init__(self, current: int, total: int):
        super().__init__(label=f"{current}/{total}", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        # 检查当前view是CombinedSearchView还是SearchResultsView
        if hasattr(self.view, 'results_view'):
            # 在CombinedSearchView中
            self.view.results_view._last_interaction = interaction
            if hasattr(self.view, 'tag_view'):
                self.view.tag_view._last_interaction = interaction
            await interaction.response.send_modal(GotoPageModal(self.view.results_view, self.view))
        else:
            # 在独立的SearchResultsView中
            self.view._last_interaction = interaction
            await interaction.response.send_modal(GotoPageModal(self.view, None))

class GotoPageModal(discord.ui.Modal, title="跳转页码"):
    def __init__(self, search_view: SearchResultsView, combined_view=None):
        super().__init__()
        self.search_view = search_view
        self.combined_view = combined_view
        
        self.page_input = discord.ui.TextInput(
            label="页码",
            placeholder=f"输入要跳转的页码 (1-{search_view.max_page})",
            required=True
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page = int(self.page_input.value)
            # 保存交互状态
            self.search_view._last_interaction = interaction
            
            if self.combined_view:
                # 在CombinedSearchView中，直接执行分页逻辑
                if hasattr(self.combined_view, 'tag_view'):
                    self.combined_view.tag_view._last_interaction = interaction
                
                # 直接执行分页逻辑，不使用临时button
                if page < 1 or page > self.search_view.max_page:
                    await interaction.response.send_message("页码超出范围。", ephemeral=True)
                    return
                
                await interaction.response.defer()
                
                offset = (page - 1) * self.search_view.per_page
                threads = await database.search_threads(
                    self.search_view.include_tags, self.search_view.exclude_tags, self.search_view.keywords,
                    self.search_view.channel_ids, self.search_view.include_authors, self.search_view.exclude_authors, 
                    self.search_view.after_ts, self.search_view.before_ts,
                    offset, self.search_view.per_page, self.search_view.sort_method, self.search_view.sort_order,
                    self.search_view.tag_logic
                )
                
                # 获取用户预览图偏好设置
                prefs = await database.get_user_search_preferences(self.search_view.user_id)
                embeds = [self.search_view.cog._build_thread_embed(t, interaction.guild, prefs.get('preview_image_mode', 'thumbnail')) for t in threads]
                self.search_view.current_page = page
                
                # 更新当前页按钮
                for item in self.combined_view.children:
                    if isinstance(item, CurrentPageButton):
                        item.label = f"{self.search_view.current_page}/{self.search_view.max_page}"
                
                # 更新内容
                tag_view = self.combined_view.tag_view
                content = tag_view._build_content_string(self.search_view.total, self.search_view.current_page, self.search_view.max_page)
                
                # 保存CombinedSearchView的状态
                tag_view._last_content = content
                tag_view._last_embeds = embeds
                
                await interaction.edit_original_response(content=content, embeds=embeds, view=self.combined_view)
            else:
                # 在独立的SearchResultsView中
                await self.search_view.go_to_page(interaction, page)
        except ValueError:
            await interaction.response.send_message("请输入有效的数字。", ephemeral=True)

# ----- 合并视图：标签选择 + 搜索结果分页 -----
class CombinedSearchView(discord.ui.View):
    def __init__(self, tag_view: TagSelectionView, results_view: SearchResultsView):
        super().__init__(timeout=900)  # 15分钟
        self.tag_view = tag_view
        self.results_view = results_view
        self._last_interaction = None  # 保存最后一次交互
        
        # 从TagSelectionView中添加所有组件 (Selects, Buttons, etc.)
        # setup方法已经为它们分配了正确的行号 (0-3)
        for item in tag_view.children:
            self.add_item(item)
        
        # 添加搜索结果分页按钮 (第4行，最多5个)
        page_buttons = [item for item in results_view.children if isinstance(item, (PageButton, CurrentPageButton))]
        for button in page_buttons[:5]:  # 最多5个按钮
            button.row = 4
            self.add_item(button)
    
    async def on_timeout(self):
        """超时处理"""
        try:
            # 创建状态字典，包含TagSelectionView和SearchResultsView的状态
            view_state = {
                'view_type': 'CombinedSearchView',
                'channel_ids': self.tag_view.channel_ids,
                'include_tags': list(self.tag_view.include_tags),
                'exclude_tags': list(self.tag_view.exclude_tags),
                'include_keywords': self.tag_view.include_keywords,
                'exclude_keywords': self.tag_view.exclude_keywords,
                'tag_logic': self.tag_view.tag_logic,
                'sort_method': self.tag_view.sort_method,
                'sort_order': self.tag_view.sort_order,
                'tag_page': self.tag_view.tag_page,
                'all_tags': self.tag_view.all_tags,
                'user_id': self.tag_view.user_id,
                'has_results': self.tag_view._has_results
            }
            
            # 如果是作者快捷搜索，添加author_id
            if isinstance(self.tag_view, AuthorTagSelectionView):
                view_state['author_id'] = self.tag_view.author_id
            
            # 创建超时视图
            timeout_view = TimeoutView(view_state)
            
            # 更新消息 - 优先使用tag_view的interaction
            interaction = self.tag_view._last_interaction or self.results_view._last_interaction
            if interaction:
                await interaction.edit_original_response(
                    content="⏰ 搜索界面已超时（15分钟），点击继续按钮恢复搜索状态",
                    view=timeout_view,
                    embeds=[]
                )
        except Exception:
            # 如果更新失败，静默处理
            pass 

# 添加"继续"按钮类
class ContinueButton(discord.ui.Button):
    def __init__(self, view_state: dict):
        super().__init__(label="🔄 继续搜索", style=discord.ButtonStyle.primary, custom_id="continue_search")
        self.view_state = view_state

    async def callback(self, interaction: discord.Interaction):
        view_type = self.view_state.get('view_type')
        
        if view_type == 'TagSelectionView':
            # 恢复TagSelectionView状态
            view = TagSelectionView(self.view_state['channel_ids'])
            view.include_tags = set(self.view_state['include_tags'])
            view.exclude_tags = set(self.view_state['exclude_tags'])
            view.include_keywords = self.view_state['include_keywords']
            view.exclude_keywords = self.view_state['exclude_keywords']
            view.tag_logic = self.view_state.get('tag_logic', 'and') # 兼容旧的状态
            view.sort_method = self.view_state['sort_method']
            view.sort_order = self.view_state['sort_order']
            view.tag_page = self.view_state['tag_page']
            view.all_tags = self.view_state['all_tags']
            
            await view.setup(interaction.guild, self.view_state['user_id'])
            
            # 如果有搜索结果，恢复搜索状态
            if self.view_state.get('has_results', False):
                await view.update_search_results(interaction, edit_original=True)
            else:
                # 没有搜索结果时，执行初始搜索
                initial_results = await view.get_initial_search_results(interaction.guild)
                mode_text = f"标签匹配: {'全部' if view.tag_logic == 'and' else '任一'}"
                
                if not initial_results['has_results']:
                    # 仍然没有结果时
                    if 'error' in initial_results:
                        content = f"选择搜索条件 - {mode_text}：\n\n❌ **搜索出错：** {initial_results['error']}"
                    else:
                        content = f"选择搜索条件 - {mode_text}：\n\n🔍 **搜索结果：** 未找到符合条件的帖子"
                    
                    # 更新view状态
                    view._last_content = content
                    view._last_embeds = []
                    view._has_results = False
                    
                    await interaction.response.edit_message(content=content, view=view, embeds=[])
                else:
                    # 有搜索结果时，创建合并视图
                    results_view = SearchResultsView(
                        view.search_cog, view.user_id,
                        [], [], "",  # 初始搜索为空条件
                        view.channel_ids, 
                        initial_results['prefs']['include_authors'] if initial_results['prefs']['include_authors'] else None,
                        initial_results['prefs']['exclude_authors'] if initial_results['prefs']['exclude_authors'] else None,
                        initial_results['prefs']['after_date'], initial_results['prefs']['before_date'],
                        1, initial_results['per_page'], initial_results['total'], 
                        view.sort_method, view.sort_order, initial_results['prefs']['tag_logic']
                    )
                    
                    # 合并两个view的按钮
                    combined_view = CombinedSearchView(view, results_view)
                    
                    content = f"选择搜索条件 - {mode_text}：\n\n🔍 **搜索结果：** 找到 {initial_results['total']} 个帖子 (第1/{results_view.max_page}页)"
                    
                    # 保存状态
                    view._last_content = content
                    view._last_embeds = initial_results['embeds']
                    view._has_results = True
                    
                    await interaction.response.edit_message(content=content, view=combined_view, embeds=initial_results['embeds'])
        
        elif view_type == 'ChannelSelectionView':
            # 恢复ChannelSelectionView状态
            # 重新获取频道列表
            all_forum_channels = [ch for ch in interaction.guild.channels if isinstance(ch, discord.ForumChannel)]
            
            # 从TagSystem获取已索引的频道ID
            tag_system = interaction.client.get_cog("TagSystem")
            if tag_system:
                indexed_channel_ids = tag_system.indexed_channel_ids
            else:
                indexed_channel_ids = set(await database.get_indexed_channel_ids())
            
            forum_channels = [ch for ch in all_forum_channels if ch.id in indexed_channel_ids]
            
            if not forum_channels:
                await interaction.response.send_message("暂无已索引的论坛频道。", ephemeral=True)
                return
            
            view = ChannelSelectionView(forum_channels)
            await interaction.response.edit_message(content="选择要搜索的频道：", view=view, embeds=[])
        
        elif view_type == 'SearchResultsView':
            # 恢复SearchResultsView状态
            search_cog = interaction.client.get_cog("Search")
            if not search_cog:
                await interaction.response.send_message("搜索功能不可用", ephemeral=True)
                return
            
            view = SearchResultsView(
                search_cog, self.view_state['user_id'],
                self.view_state['include_tags'], self.view_state['exclude_tags'],
                self.view_state['keywords'], self.view_state['channel_ids'],
                self.view_state['include_authors'], self.view_state['exclude_authors'],
                self.view_state['after_ts'], self.view_state['before_ts'],
                self.view_state['current_page'], self.view_state['per_page'],
                self.view_state['total'], self.view_state['sort_method'],
                self.view_state['sort_order'], self.view_state['tag_logic']
            )
            
            # 恢复当前页的搜索结果
            await view.go_to_page(interaction, self.view_state['current_page'])
        
        elif view_type == 'CombinedSearchView':
            # 恢复CombinedSearchView状态 - 先恢复TagSelectionView
            # 检查是否是作者快捷搜索
            if 'author_id' in self.view_state:
                # 恢复AuthorTagSelectionView
                tag_view = AuthorTagSelectionView(self.view_state['channel_ids'], self.view_state['author_id'])
            else:
                # 恢复普通TagSelectionView
                tag_view = TagSelectionView(self.view_state['channel_ids'])
            
            tag_view.include_tags = set(self.view_state['include_tags'])
            tag_view.exclude_tags = set(self.view_state['exclude_tags'])
            tag_view.include_keywords = self.view_state['include_keywords']
            tag_view.exclude_keywords = self.view_state['exclude_keywords']
            tag_view.tag_logic = self.view_state.get('tag_logic', 'and') # 兼容旧的状态
            tag_view.sort_method = self.view_state['sort_method']
            tag_view.sort_order = self.view_state['sort_order']
            tag_view.tag_page = self.view_state['tag_page']
            tag_view.all_tags = self.view_state['all_tags']
            
            await tag_view.setup(interaction.guild, self.view_state['user_id'])
            
            # 恢复搜索结果
            await tag_view.update_search_results(interaction, edit_original=True)

class TimeoutView(discord.ui.View):
    def __init__(self, view_state: dict):
        super().__init__(timeout=None)
        self.add_item(ContinueButton(view_state))

# ----- 作者快捷搜索视图 -----
class AuthorTagSelectionView(TagSelectionView):
    def __init__(self, channel_ids, author_id: int):
        super().__init__(channel_ids)
        self.author_id = author_id  # 指定的作者ID
        
    async def setup(self, guild: discord.Guild, user_id: int = None):
        """获取作者标签并设置UI"""
        self.user_id = user_id
        
        # 获取指定作者的标签
        self.all_tags = await database.get_tags_for_author(self.author_id)
        
        # 清空现有items
        self.clear_items()
        
        # 计算当前页的标签
        start_idx = self.tag_page * self.tags_per_page
        end_idx = start_idx + self.tags_per_page
        current_page_tags = self.all_tags[start_idx:end_idx]
        
        # 第 0 行: 正选标签
        include_options = [discord.SelectOption(label=tag_name, value=tag_name) for _, tag_name in current_page_tags]
        self.add_item(IncludeTagSelect(include_options, list(self.include_tags)))

        # 第 1 行: 反选标签
        exclude_options = [discord.SelectOption(label=tag_name, value=tag_name) for _, tag_name in current_page_tags]
        self.add_item(ExcludeTagSelect(exclude_options, list(self.exclude_tags)))
        
        # 第 2 行: 控制按钮
        keyword_button = KeywordButton()
        keyword_button.row = 2
        self.add_item(keyword_button)

        if len(self.all_tags) > self.tags_per_page:
            self.add_item(TagPageButton("◀️ 上一页", "prev"))

        tag_logic_button = TagLogicButton(self.tag_logic)
        tag_logic_button.row = 2
        self.add_item(tag_logic_button)

        if len(self.all_tags) > self.tags_per_page:
            self.add_item(TagPageButton("▶️ 下一页", "next"))
            
        sort_order_button = SortOrderButton(self.sort_order)
        sort_order_button.row = 2
        self.add_item(sort_order_button)
        
        # 第 3 行: 排序选择器
        sort_select = SortMethodSelect(self.sort_method)
        sort_select.row = 3
        self.add_item(sort_select)

    async def get_initial_search_results(self, guild: discord.Guild):
        """获取初始搜索结果（显示指定作者的所有帖子，忽略用户偏好）"""
        try:
            # 初始搜索：空标签，空关键词，但强制限制作者
            include_tags = []
            exclude_tags = []
            include_keywords = ""
            
            per_page = await database.get_results_per_page(self.user_id)
            
            # 忽略用户偏好，强制使用指定作者
            include_authors = [self.author_id]
            exclude_authors = None
            after_ts = None
            before_ts = None
            # 获取用户偏好中的标签逻辑
            prefs = await database.get_user_search_preferences(self.user_id)
            tag_logic = prefs.get('tag_logic', 'and')
            self.tag_logic = tag_logic # 同步到view实例
            
            total = await database.count_threads_for_search(
                include_tags, exclude_tags, include_keywords, 
                self.channel_ids, include_authors, exclude_authors, after_ts, before_ts,
                tag_logic
            )
            
            if total == 0:
                # 没有结果时只返回基本信息
                return {
                    'total': 0,
                    'threads': [],
                    'embeds': [],
                    'has_results': False
                }
            
            threads = await database.search_threads(
                include_tags, exclude_tags, include_keywords,
                self.channel_ids, include_authors, exclude_authors, after_ts, before_ts,
                0, per_page, self.sort_method, self.sort_order, tag_logic
            )
            
            # 获取搜索cog来构建embed
            if not self.search_cog:
                # 通过guild.me获取bot实例
                if hasattr(guild, 'me') and guild.me:
                    bot = guild.me._state._get_client()
                    self.search_cog = bot.get_cog("Search")
                    
            # 如果缓存已失效，重新缓存标签
            if self.search_cog and hasattr(self.search_cog, 'cache_channel_tags'):
                # 检查是否需要更新缓存
                if not self.search_cog.channel_tags_cache:
                    await self.search_cog.cache_channel_tags()
                    
            # 对于作者快捷搜索，固定使用缩略图模式
            embeds = [self.search_cog._build_thread_embed(t, guild, 'thumbnail') for t in threads]
            
            return {
                'total': total,
                'threads': threads,
                'embeds': embeds,
                'has_results': True,
                'per_page': per_page,
                'prefs': {
                    'include_authors': include_authors,
                    'exclude_authors': exclude_authors,
                    'after_date': after_ts,
                    'before_date': before_ts,
                    'tag_logic': tag_logic,
                    'preview_image_mode': 'thumbnail'
                }
            }
            
        except Exception as e:
            print(f"作者快捷搜索出错: {e}")
            return {
                'total': 0,
                'threads': [],
                'embeds': [],
                'has_results': False,
                'error': str(e)
            }

    async def update_search_results(self, interaction: discord.Interaction, *, edit_original: bool = True):
        """
        更新搜索结果（作者快捷搜索版本）
        此方法现在只是调用父类的同名方法，因为大部分逻辑已经可以复用。
        """
        # 直接调用父类的 update_search_results 方法
        await super().update_search_results(interaction, edit_original=edit_original)
