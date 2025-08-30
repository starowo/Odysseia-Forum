import discord
from shared.ranking_config import RankingConfig

class ConfigEmbedBuilder:
    """构建与排序配置相关的 Discord Embeds"""

    @staticmethod
    def build_config_updated_embed(config_name: str) -> discord.Embed:
        """构建配置更新成功的 embed"""
        embed = discord.Embed(
            title="✅ 排序算法配置已更新",
            description=f"当前配置：**{config_name}**",
            color=0x00FF00,
        )

        embed.add_field(
            name="权重配置",
            value=f"• 时间权重：**{RankingConfig.TIME_WEIGHT_FACTOR:.1%}**\n"
            f"• 标签权重：**{RankingConfig.TAG_WEIGHT_FACTOR:.1%}**\n"
            f"• 反应权重：**{RankingConfig.REACTION_WEIGHT_FACTOR:.1%}**\n"
            f"• 时间衰减率：**{RankingConfig.TIME_DECAY_RATE}**\n"
            f"• 反应对数基数：**{RankingConfig.REACTION_LOG_BASE}**",
            inline=True,
        )

        embed.add_field(
            name="惩罚机制",
            value=f"• 严重惩罚阈值：**{RankingConfig.SEVERE_PENALTY_THRESHOLD}**\n"
            f"• 轻度惩罚阈值：**{RankingConfig.MILD_PENALTY_THRESHOLD}**\n"
            f"• 严重惩罚系数：**{RankingConfig.SEVERE_PENALTY_FACTOR}**",
            inline=True,
        )

        embed.add_field(
            name="算法说明",
            value="新的排序算法将立即生效，影响所有后续搜索结果。\n"
            "时间权重基于指数衰减，标签权重基于Wilson Score算法。",
            inline=False,
        )
        return embed

    @staticmethod
    def build_view_config_embed() -> discord.Embed:
        """构建查看当前配置的 embed"""
        embed = discord.Embed(
            title="🔧 当前排序算法配置",
            description="智能混合权重排序算法参数",
            color=0x3498DB,
        )

        embed.add_field(
            name="权重配置",
            value=f"• 时间权重：**{RankingConfig.TIME_WEIGHT_FACTOR:.1%}**\n"
            f"• 标签权重：**{RankingConfig.TAG_WEIGHT_FACTOR:.1%}**\n"
            f"• 反应权重：**{RankingConfig.REACTION_WEIGHT_FACTOR:.1%}**\n"
            f"• 时间衰减率：**{RankingConfig.TIME_DECAY_RATE}**\n"
            f"• 反应对数基数：**{RankingConfig.REACTION_LOG_BASE}**",
            inline=True,
        )

        embed.add_field(
            name="惩罚机制",
            value=f"• 严重惩罚阈值：**{RankingConfig.SEVERE_PENALTY_THRESHOLD}**\n"
            f"• 轻度惩罚阈值：**{RankingConfig.MILD_PENALTY_THRESHOLD}**\n"
            f"• 严重惩罚系数：**{RankingConfig.SEVERE_PENALTY_FACTOR:.1%}**\n"
            f"• 轻度惩罚系数：**{RankingConfig.MILD_PENALTY_FACTOR:.1%}**",
            inline=True,
        )

        embed.add_field(
            name="算法特性",
            value="• **Wilson Score**：置信度评估标签质量\n"
            "• **指数衰减**：时间新鲜度自然衰减\n"
            "• **智能惩罚**：差评内容自动降权\n"
            "• **可配置权重**：灵活调整排序偏好",
            inline=False,
        )

        embed.set_footer(text="管理员可使用 /排序算法配置 命令调整参数")
        return embed