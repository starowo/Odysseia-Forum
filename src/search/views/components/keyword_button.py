import discord
from shared.default_preferences import DefaultPreferences


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

        self.include_input = discord.ui.TextInput(
            label="包含关键词（逗号或斜杠分隔）",
            placeholder="必须包含的关键词",
            required=False,
            default=initial_keywords,
            row=0,
        )
        self.add_item(self.include_input)

        self.exclude_input = discord.ui.TextInput(
            label="排除关键词（逗号分隔）",
            placeholder="不能包含的关键词",
            required=False,
            default=initial_exclude_keywords,
            row=1,
        )
        self.add_item(self.exclude_input)

        self.exemption_markers_input = discord.ui.TextInput(
            label="排除关键词的豁免标记（逗号分隔）",
            placeholder="例如：禁, 🈲",
            required=False,
            default=initial_exemption_markers,
            row=2,
        )
        self.add_item(self.exemption_markers_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.submit_callback(
            interaction,
            self.include_input.value,
            self.exclude_input.value,
            self.exemption_markers_input.value,
        )


class KeywordButton(discord.ui.Button):
    def __init__(self, press_callback, row: int = 2):
        super().__init__(
            label="📝 关键词", style=discord.ButtonStyle.secondary, row=row
        )
        self.press_callback = press_callback

    async def callback(self, interaction: discord.Interaction):
        await self.press_callback(interaction)
