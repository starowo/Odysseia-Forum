from typing import List, Optional

import discord

from search.constants import SortMethod


class SortMethodSelect(discord.ui.Select):
    def __init__(
        self,
        current_sort: str,
        update_callback,
        row: int = 0,
        exclude_values: Optional[List[str]] = None,
        placeholder: str = "选择自定义排序的基础算法...",
    ):
        options = []
        exclude_set = set(exclude_values or [])

        for method in SortMethod:
            info = method.value
            if info.value in exclude_set:
                continue

            options.append(
                discord.SelectOption(
                    label=info.label,
                    value=info.value,
                    description=info.description,
                    default=(current_sort == info.value),
                )
            )

        super().__init__(placeholder=placeholder, options=options, row=row)
        self.update_callback = update_callback

    async def callback(self, interaction: discord.Interaction):
        await self.update_callback(interaction, self.values[0])
