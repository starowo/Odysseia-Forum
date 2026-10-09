from typing import cast

import discord
from discord.ui import Label


class KeywordModal(discord.ui.Modal, title="设置关键词过滤"):
    def __init__(
        self,
        initial_keywords: str,
        initial_exclude_keywords: str,
        submit_callback,
        initial_exemption_markers: str,
    ):
        super().__init__()
        self.submit_callback = submit_callback

        # 包含关键词
        self.include_input = discord.ui.TextInput(
            placeholder="必须包含的关键词",
            required=False,
            default=initial_keywords,
        )

        self.add_item(
            Label(
                text="包含关键词（逗号或斜杠分隔）",
                description="输入 'A/B/C'，返回帖子将包含 A B C 中任意一个。  "
                "\n\n输入'C, D'，返回帖子同时包含 C 和 D",
                component=self.include_input,
            )
        )

        # 排除关键词
        self.exclude_input = discord.ui.TextInput(
            placeholder="不能包含的关键词",
            required=False,
            default=initial_exclude_keywords,
        )

        self.add_item(
            Label(
                text="排除关键词（逗号分隔）",
                description="屏蔽包含任一关键词的卡贴",
                component=self.exclude_input,
            )
        )

        # 豁免标记
        self.exemption_markers_input = discord.ui.TextInput(
            placeholder="例如：禁, 🈲",
            required=False,
            default=initial_exemption_markers,
        )

        self.add_item(
            Label(
                text="排除关键词的豁免标记（逗号分隔）",
                description="解除对排除关键词附近存在标记词的卡帖的屏蔽",
                component=self.exemption_markers_input,
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        # 从 Label 的 .component 属性获取 TextInput
        include_label_item = cast(Label, self.children[0])
        include_input = cast(discord.ui.TextInput, include_label_item.component)
        exclude_label_item = cast(Label, self.children[1])
        exclude_input = cast(discord.ui.TextInput, exclude_label_item.component)
        exemption_label_item = cast(Label, self.children[2])
        exemption_markers_input = cast(
            discord.ui.TextInput, exemption_label_item.component
        )

        await self.submit_callback(
            interaction,
            include_input.value,
            exclude_input.value,
            exemption_markers_input.value,
        )


class KeywordButton(discord.ui.Button):
    def __init__(self, press_callback, row: int = 2):
        super().__init__(
            label="📝 关键词", style=discord.ButtonStyle.secondary, row=row
        )
        self.press_callback = press_callback

    async def callback(self, interaction: discord.Interaction):
        await self.press_callback(interaction)
