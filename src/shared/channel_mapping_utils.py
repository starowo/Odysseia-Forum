from typing import Dict, List, Optional, Set
from dto.search import ChannelMappingResolutionDTO


class ChannelMappingUtils:
    """处理频道与虚拟标签映射逻辑的工具类"""

    def __init__(self, channel_mappings_config: Dict[int, List[Dict]]):
        self.channel_mappings = channel_mappings_config

    def resolve(
        self,
        channel_ids: Optional[List[int]],
        include_tags: List[str],
        exclude_tags: List[str],
        tag_logic: str,
        all_indexed_channels: List[int],
    ) -> ChannelMappingResolutionDTO:
        """解析频道和标签映射，转换为实际的数据库查询参数"""
        result = ChannelMappingResolutionDTO(
            effective_channel_ids=[],
            effective_include_tags=list(include_tags),
            effective_exclude_tags=list(exclude_tags),
            searched_ids=set(),
            has_mapping=False,
        )

        # 建立全局虚拟标签字典（用于识别虚拟标签和处理反选排除）
        global_virtual_tag_to_channels: Dict[str, Set[int]] = {}
        for target_channel, mappings in self.channel_mappings.items():
            for mapping in mappings:
                tag_name = mapping["tag_name"]
                global_virtual_tag_to_channels.setdefault(tag_name, set()).update(
                    mapping.get("source_channel_ids", [])
                )

        # 分离真实标签和虚拟标签
        included_virtual_tags = [
            tag for tag in include_tags if tag in global_virtual_tag_to_channels
        ]
        excluded_virtual_tags = [
            tag for tag in exclude_tags if tag in global_virtual_tag_to_channels
        ]

        # 过滤掉虚拟标签，留下真实标签用于数据库查询
        result.effective_include_tags = [
            tag for tag in include_tags if tag not in global_virtual_tag_to_channels
        ]
        result.effective_exclude_tags = [
            tag for tag in exclude_tags if tag not in global_virtual_tag_to_channels
        ]

        if included_virtual_tags or excluded_virtual_tags:
            result.has_mapping = True

        # 计算反选排除频道（基于全局，只要命中虚拟标签就排除其所有源频道）
        excluded_channels = set()
        for virtual_tag in excluded_virtual_tags:
            excluded_channels.update(global_virtual_tag_to_channels[virtual_tag])

        # 计算正选频道范围
        final_channels: Set[int] = set()

        if channel_ids:
            # --- 情况 A: 选择了具体频道 ---
            real_channels_set = set(channel_ids)

            # 构建“选中频道对应的虚拟标签字典”
            selected_tag_to_channels: Dict[str, Set[int]] = {}
            all_sources_for_selected: Set[int] = set()
            for ch_id in channel_ids:
                for mapping in self.channel_mappings.get(ch_id, []):
                    tag_name = mapping["tag_name"]
                    src_ids = mapping.get("source_channel_ids", [])
                    selected_tag_to_channels.setdefault(tag_name, set()).update(src_ids)
                    all_sources_for_selected.update(src_ids)

            if included_virtual_tags:
                # --- 分支: 选择了频道，且正选了虚拟标签 ---
                # 仅在选中频道定义的范围内计算虚拟标签对应的频道
                virtual_channels = set()
                if tag_logic == "and":
                    virtual_channels = set(
                        selected_tag_to_channels.get(included_virtual_tags[0], [])
                    )
                    for tag in included_virtual_tags[1:]:
                        virtual_channels &= selected_tag_to_channels.get(tag, set())
                else:
                    for tag in included_virtual_tags:
                        virtual_channels.update(
                            selected_tag_to_channels.get(tag, set())
                        )

                # 搜索频道 = 虚拟标签对应频道 - 反选频道 (此时不再包含 real_channels)
                final_channels = virtual_channels - excluded_channels
            else:
                # --- 分支: 选择了频道，但没有正选虚拟标签 ---
                # 搜索频道 = 选中的真实频道 + 选中频道下所有可能的虚拟源频道 - 反选频道
                final_channels = (
                    real_channels_set | all_sources_for_selected
                ) - excluded_channels

        else:
            # --- 情况 B: 未选择频道（全局搜索） ---
            if included_virtual_tags:
                # 选择了虚拟标签
                virtual_channels = set()
                if tag_logic == "and":
                    virtual_channels = set(
                        global_virtual_tag_to_channels[included_virtual_tags[0]]
                    )
                    for tag in included_virtual_tags[1:]:
                        virtual_channels &= global_virtual_tag_to_channels[tag]
                else:
                    for tag in included_virtual_tags:
                        virtual_channels.update(global_virtual_tag_to_channels[tag])
                final_channels = virtual_channels - excluded_channels
            else:
                # 既没选频道也没选虚拟标签：所有已索引频道 - 反选频道
                final_channels = set(all_indexed_channels) - excluded_channels

        # 结果封装与优化
        # 如果最终计算出的频道集合涵盖了所有已知索引频道，则传 None 以优化数据库查询
        if final_channels == set(all_indexed_channels):
            result.effective_channel_ids = None
        else:
            result.effective_channel_ids = list(final_channels)

        result.searched_ids = final_channels
        return result

    def get_channel_virtual_tags_map(
        self, origin_channel_ids: List[int]
    ) -> Dict[int, List[str]]:
        """构建源频道ID到虚拟标签名称的映射字典"""
        channel_to_virtual = {}
        for origin_id in origin_channel_ids:
            for mapping in self.channel_mappings.get(origin_id, []):
                for source_channel_id in mapping.get("source_channel_ids", []):
                    channel_to_virtual.setdefault(source_channel_id, []).append(
                        mapping["tag_name"]
                    )
        return channel_to_virtual

    def get_all_channel_virtual_tags_map(self) -> Dict[int, List[str]]:
        """构建所有源频道ID到虚拟标签名称的完整映射字典"""
        channel_to_virtual = {}
        for target_ch, mappings in self.channel_mappings.items():
            for m in mappings:
                for src_id in m.get("source_channel_ids", []):
                    channel_to_virtual.setdefault(src_id, []).append(m["tag_name"])
        return channel_to_virtual
