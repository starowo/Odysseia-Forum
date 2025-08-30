import discord


class SortMethodSelect(discord.ui.Select):
    def __init__(self, current_sort: str, update_callback, row: int = 0):
        options = [
            discord.SelectOption(
                label="🧠 综合排序",
                value="comprehensive",
                description="智能混合权重算法（时间+标签+反应）",
                default=(current_sort == "comprehensive"),
            ),
            discord.SelectOption(
                label="🕐 按发帖时间",
                value="created_at",
                description="按帖子创建时间排列",
                default=(current_sort == "created_at"),
            ),
            discord.SelectOption(
                label="⏰ 按活跃时间",
                value="last_active_at",
                description="按最近活跃时间排列",
                default=(current_sort == "last_active_at"),
            ),
            discord.SelectOption(
                label="🎉 按反应数",
                value="reaction_count",
                description="按最高反应数排列",
                default=(current_sort == "reaction_count"),
            ),
            discord.SelectOption(
                label="💬 按回复数",
                value="reply_count",
                description="按帖子回复数量排列",
                default=(current_sort == "reply_count"),
            ),
        ]
        super().__init__(placeholder="选择排序方式...", options=options, row=row)
        self.update_callback = update_callback

    async def callback(self, interaction: discord.Interaction):
        await self.update_callback(interaction, self.values[0])
