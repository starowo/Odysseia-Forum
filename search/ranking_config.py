# 智能搜索排序算法配置文件
# 可以根据实际使用情况调整这些参数

class RankingConfig:
    """搜索结果排序算法配置"""
    
    # =====  权重分配 =====
    TIME_WEIGHT_FACTOR = 0.5       # 时间权重因子 (0-1)
    TAG_WEIGHT_FACTOR = 0.3        # 标签权重因子 (0-1)  
    REACTION_WEIGHT_FACTOR = 0.2   # 反应权重因子 (0-1)
    
    # =====  时间衰减参数 =====
    TIME_DECAY_RATE = 0.1          # 时间衰减率，越大衰减越快
    # 说明：0.1对应约7天半衰期，0.05对应约14天半衰期
    
    # =====  标签评分参数 =====
    WILSON_CONFIDENCE_LEVEL = 1.96  # Wilson Score置信水平 (1.96 = 95%)
    DEFAULT_TAG_SCORE = 0.5         # 无评价时的默认标签评分
    
    # =====  反应数归一化参数 =====
    REACTION_LOG_BASE = 50          # 反应数对数归一化基数
    MAX_REACTION_SCORE = 1.0        # 反应权重最大值
    # 说明：reaction_weight = min(1.0, log(reactions + 1) / log(base + 1))
    
    # =====  惩罚机制参数 =====
    SEVERE_PENALTY_THRESHOLD = 0.2  # 严重差评阈值
    SEVERE_PENALTY_MIN_VOTES = 5    # 严重惩罚最少评价数
    SEVERE_PENALTY_FACTOR = 0.1     # 严重惩罚系数
    
    MILD_PENALTY_THRESHOLD = 0.35   # 轻度差评阈值  
    MILD_PENALTY_MIN_VOTES = 10     # 轻度惩罚最少评价数
    MILD_PENALTY_FACTOR = 0.5       # 轻度惩罚系数
    
    # =====  显示配置 =====
    SHOW_RANKING_INFO = True        # 是否在搜索结果中显示排序信息
    RANKING_PRECISION = 0           # 排序权重显示精度 (小数位数)
    
    @classmethod
    def validate(cls):
        """验证配置参数的合理性"""
        # 检查权重因子
        weight_sum = cls.TIME_WEIGHT_FACTOR + cls.TAG_WEIGHT_FACTOR + cls.REACTION_WEIGHT_FACTOR
        assert abs(weight_sum - 1.0) < 0.001, f"三个权重因子之和必须为1，当前为{weight_sum}"
        
        assert 0 <= cls.TIME_WEIGHT_FACTOR <= 1, "时间权重因子必须在0-1之间"
        assert 0 <= cls.TAG_WEIGHT_FACTOR <= 1, "标签权重因子必须在0-1之间"
        assert 0 <= cls.REACTION_WEIGHT_FACTOR <= 1, "反应权重因子必须在0-1之间"
        
        assert cls.TIME_DECAY_RATE > 0, "时间衰减率必须大于0"
        assert 0 <= cls.DEFAULT_TAG_SCORE <= 1, "默认标签评分必须在0-1之间"
        assert cls.REACTION_LOG_BASE > 0, "反应数对数基数必须大于0"
        
        assert 0 <= cls.SEVERE_PENALTY_THRESHOLD <= 1, "严重惩罚阈值必须在0-1之间"
        assert 0 <= cls.MILD_PENALTY_THRESHOLD <= 1, "轻度惩罚阈值必须在0-1之间"
        assert cls.SEVERE_PENALTY_THRESHOLD < cls.MILD_PENALTY_THRESHOLD, "严重惩罚阈值必须小于轻度惩罚阈值"
        print("✅ 排序算法配置验证通过")

# 在启动时验证配置
RankingConfig.validate()

# 预设配置方案
class PresetConfigs:
    """预设的配置方案"""
    
    @staticmethod
    def time_focused():
        """偏重时间新鲜度的配置"""
        RankingConfig.TIME_WEIGHT_FACTOR = 0.6
        RankingConfig.TAG_WEIGHT_FACTOR = 0.2
        RankingConfig.REACTION_WEIGHT_FACTOR = 0.2
        RankingConfig.TIME_DECAY_RATE = 0.05  # 更慢的衰减
    
    @staticmethod
    def quality_focused():
        """偏重内容质量的配置"""
        RankingConfig.TIME_WEIGHT_FACTOR = 0.3
        RankingConfig.TAG_WEIGHT_FACTOR = 0.5
        RankingConfig.REACTION_WEIGHT_FACTOR = 0.2
        RankingConfig.TIME_DECAY_RATE = 0.15  # 更快的衰减
    
    @staticmethod
    def popularity_focused():
        """偏重受欢迎程度的配置"""
        RankingConfig.TIME_WEIGHT_FACTOR = 0.3
        RankingConfig.TAG_WEIGHT_FACTOR = 0.2
        RankingConfig.REACTION_WEIGHT_FACTOR = 0.5
        RankingConfig.REACTION_LOG_BASE = 30  # 更敏感的反应数评分
    
    @staticmethod
    def balanced():
        """平衡配置（默认）"""
        RankingConfig.TIME_WEIGHT_FACTOR = 0.5
        RankingConfig.TAG_WEIGHT_FACTOR = 0.3
        RankingConfig.REACTION_WEIGHT_FACTOR = 0.2
        RankingConfig.TIME_DECAY_RATE = 0.1
        RankingConfig.REACTION_LOG_BASE = 50
    
    @staticmethod
    def strict_quality():
        """严格质量控制配置"""
        RankingConfig.TIME_WEIGHT_FACTOR = 0.4
        RankingConfig.TAG_WEIGHT_FACTOR = 0.4
        RankingConfig.REACTION_WEIGHT_FACTOR = 0.2
        RankingConfig.SEVERE_PENALTY_THRESHOLD = 0.3
        RankingConfig.MILD_PENALTY_THRESHOLD = 0.5
        RankingConfig.SEVERE_PENALTY_FACTOR = 0.05  # 更严厉的惩罚 