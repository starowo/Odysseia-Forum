class NullBot:
    """占位 Bot 对象，让 API 进程无需 discord.py 即可使用 CacheService 接口"""

    def get_channel(self, channel_id):
        return None

    def get_user(self, user_id):
        return None

    def dispatch(self, event, *args, **kwargs):
        pass
