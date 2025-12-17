from typing import Awaitable, Callable, List, Set

import discord


class TagSelect(discord.ui.Select):
    def __init__(
        self,
        all_tags: List[str],
        selected_tags: Set[str],
        page: int,
        tags_per_page: int,
        placeholder_prefix: str,
        custom_id: str,
        on_change_callback: Callable[[discord.Interaction, Set[str]], Awaitable[None]],
        **kwargs,
    ):
        self.all_tags = all_tags
        self.selected_tags = selected_tags
        self.tag_page = page
        self.tags_per_page = tags_per_page
        self.on_change_callback = on_change_callback
        self.custom_id_prefix = custom_id  # 用作标识，例如 "generic_include_tags"

        start_idx = self.tag_page * self.tags_per_page
        end_idx = start_idx + self.tags_per_page
        current_page_tags = self.all_tags[start_idx:end_idx]

        # 去重
        seen_tags = set()
        unique_current_page_tags = []
        for tag in current_page_tags:
            if tag not in seen_tags:
                seen_tags.add(tag)
                unique_current_page_tags.append(tag)

        options = [
            discord.SelectOption(label=tag_name, value=tag_name)
            for tag_name in unique_current_page_tags
        ]

        if self.selected_tags:
            placeholder_text = f"已{placeholder_prefix}: " + ", ".join(
                sorted(list(self.selected_tags))
            )
            if len(placeholder_text) > 100:
                placeholder_text = placeholder_text[:97] + "..."
        else:
            placeholder_text = (
                f"选择要{placeholder_prefix}的标签 (第 {self.tag_page + 1} 页)"
            )

        super().__init__(
            placeholder=placeholder_text,
            options=options
            if options
            else [discord.SelectOption(label="无可用标签", value="no_tags")],
            min_values=0,
            max_values=len(options) if options else 1,
            custom_id=custom_id,
            disabled=not options,
            **kwargs,
        )

        for option in self.options:
            if option.value in self.selected_tags:
                option.default = True

    async def callback(self, interaction: discord.Interaction):
        current_page_tag_names = {
            opt.value for opt in self.options if opt.value != "no_tags"
        }

        tags_on_other_pages = {
            tag_name
            for tag_name in self.selected_tags
            if tag_name not in current_page_tag_names
        }

        new_selections = {v for v in self.values if v != "no_tags"}

        final_selection = tags_on_other_pages.union(new_selections)

        await self.on_change_callback(interaction, final_selection)
