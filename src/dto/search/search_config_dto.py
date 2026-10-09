from pydantic import BaseModel, Field

from shared.enum import SearchConfigDefaults


class SearchConfigDTO(BaseModel):
    """
    搜索算法配置的数据传输对象。
    包含 UCB1 和 Reddit Hot 两种排序算法的可配置参数。
    """

    total_display_count: int = Field(
        default=1,
        description="总展示次数 (N)，用于 UCB1 公式分母",
    )
    exploration_factor: float = Field(
        default=SearchConfigDefaults.UCB1_EXPLORATION_FACTOR.value,
        description="UCB1 探索因子 (C)，即 sqrt(2)",
    )
    strength_weight: float = Field(
        default=SearchConfigDefaults.STRENGTH_WEIGHT.value,
        description="实力分权重 (W)",
    )
    reddit_hot_time_decay: float = Field(
        default=SearchConfigDefaults.REDDIT_HOT_TIME_DECAY.value,
        description="Reddit Hot 时间衰减常量（秒），越大好帖子停留越久",
    )
