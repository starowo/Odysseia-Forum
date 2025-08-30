import discord


class SearchButton(discord.ui.Button):
    def __init__(self, search_callback):
        super().__init__(label="🔍 执行搜索", style=discord.ButtonStyle.success, row=4)
        self.search_callback = search_callback

    async def callback(self, interaction: discord.Interaction):
        await self.search_callback(interaction)
