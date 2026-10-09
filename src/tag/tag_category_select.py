import discord

from dto.events.tag_command import TagCommand
from shared.enum.tag_category import TagCategory
from shared.tag_error import TagError


class TagCategorySelect(
    discord.ui.DynamicItem[discord.ui.Select],
    template=r"tag_classify:(?P<tag_id>[0-9]+)",
):
    """可跨重启恢复的标签分类选择器，权限在领域入口实时检查。"""

    def __init__(self, tag_id):
        """构造七类选项并将内部标签 ID 写入可恢复组件标识。"""
        self.tag_id = int(tag_id)
        super().__init__(
            discord.ui.Select(
                custom_id=f"tag_classify:{self.tag_id}",
                placeholder="BOT 管理员选择分类",
                options=[
                    discord.SelectOption(label=item.name, value=str(item.value))
                    for item in TagCategory
                ],
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        """从持久化组件 ID 恢复目标，不依赖内存中的旧消息对象。"""
        return cls(int(match["tag_id"]))

    async def callback(self, interaction):
        """提交分类，权限不足和名称冲突不修改原标签。"""
        await interaction.response.defer(ephemeral=True)
        cog = interaction.client.get_cog("TagCog")
        if cog is None:
            await interaction.followup.send("标签服务暂不可用", ephemeral=True)
            return
        try:
            result = await cog.mediator.request(
                TagCommand(
                    "manage",
                    interaction.user.id,
                    {
                        "operation": "classify",
                        "tag_id": self.tag_id,
                        "category": int(self.item.values[0]),
                    },
                )
            )
            await interaction.followup.send(
                f"已分类：{result['category_name']}:{result['name']}", ephemeral=True
            )
            await interaction.message.edit(view=None)
        except TagError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
