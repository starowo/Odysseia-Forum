from enum import Enum
from typing import Optional


class SortMethodInfo:
    """用于存储排序方法详细信息的数据类"""

    def __init__(
        self,
        value: str,
        label: str,
        description: str,
        short_label: Optional[str] = None,
    ):
        self.value = value
        self.label = label
        self.description = description
        # 如果未提供 short_label，则从 label 自动生成
        self.short_label = (
            short_label
            if short_label is not None
            else label.split(" ")[-1].replace("排序", "")
        )


class SortMethod(Enum):
    """定义所有可用排序方法的枚举"""

    COMPREHENSIVE = SortMethodInfo(
        value="comprehensive",
        label="🧠 综合排序",
        description="UCB1 排序算法",
        short_label="综合",
    )
    CREATED_AT = SortMethodInfo(
        value="created_at",
        label="🕐 按发帖时间",
        description="按帖子创建时间排列",
        short_label="发帖时间",
    )
    LAST_ACTIVE_AT = SortMethodInfo(
        value="last_active_at",
        label="⏰ 按活跃时间",
        description="按最近活跃时间排列",
        short_label="活跃时间",
    )
    REACTION_COUNT = SortMethodInfo(
        value="reaction_count",
        label="🎉 按反应数",
        description="按最高反应数排列",
        short_label="反应数",
    )
    REPLY_COUNT = SortMethodInfo(
        value="reply_count",
        label="💬 按回复数",
        description="按帖子回复数量排列",
        short_label="回复数",
    )
    COLLECTION_COUNT = SortMethodInfo(
        value="collection_count",
        label="⭐ 按收藏数",
        description="按帖子被收藏的数量排列",
        short_label="收藏数",
    )
    REDDIT_HOT = SortMethodInfo(
        value="reddit_hot",
        label="🔥 热门排序",
        description="Reddit Hot 算法：log(反应数) + 时间加成",
        short_label="热门",
    )
    CUSTOM = SortMethodInfo(
        value="custom",
        label="🛠️ 自定义搜索",
        description="设置更精细的筛选条件和排序",
        # 自定义模式没有 short_label，因为它本身不是一个基础排序
    )

    @staticmethod
    def get_label_by_value(value: str, default: str = "综合排序") -> str:
        """
        根据排序方法的 value 安全地获取其 label。

        Args:
            value (str): 要查找的排序方法 value。
            default (str): 如果找不到，返回的默认标签。

        Returns:
            str: 对应的标签或默认值。
        """
        for item in SortMethod:
            if item.value.value == value:
                return item.value.label
        return default

    @staticmethod
    def get_short_label_by_value(value: str, default: str = "综合") -> str:
        """
        根据排序方法的 value 安全地获取其 short_label。
        """
        for item in SortMethod:
            if item.value.value == value:
                # CUSTOM 没有 short_label，返回一个合理的默认值
                return item.value.short_label or default
        return default
