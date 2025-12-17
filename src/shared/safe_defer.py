import logging

import discord

# 获取一个模块级别的 logger
logger = logging.getLogger(__name__)


async def safe_defer(interaction: discord.Interaction, ephemeral: bool = True):
    """
    一个安全的“占坑”函数。
    它会检查交互是否已被响应，如果没有，就立即以指定的方式延迟响应

    :param interaction: 要延迟的交互对象。
    :param ephemeral: 是否将“占坑”消息设置为仅自己可见。默认为 True。
    """
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=ephemeral)
        except discord.errors.InteractionResponded:
            # 在罕见的竞态条件下（在 is_done() 检查和 defer() 调用之间，另一个任务响应了此交互），
            # 我们在此处添加日志记录，以便在它频繁发生时能够进行调试。
            logger.warning(f"safe_defer: 交互 {interaction.id} 在竞态条件下已被响应。")
            pass
