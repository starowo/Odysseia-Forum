"""Discord 成员事件驱动的认证缓存失效测试。"""

from types import SimpleNamespace

import pytest

from author.cog import AuthorCog
from shared.redis_client import RedisManager


class FakeRedis:
    """记录成员事件请求删除的 Redis 键。"""

    def __init__(self):
        """初始化删除记录。"""
        self.deleted_keys: list[str] = []

    async def delete(self, key: str) -> int:
        """记录删除键并模拟删除成功。"""
        self.deleted_keys.append(key)
        return 1


@pytest.mark.asyncio
async def test_role_change_deletes_member_cache(monkeypatch):
    """身份组发生变化时只删除缓存，不覆盖成员快照。"""
    fake_redis = FakeRedis()
    monkeypatch.setattr(RedisManager, "get_client", lambda: fake_redis)
    before = SimpleNamespace(id=123, roles=[1])
    after = SimpleNamespace(id=123, roles=[1, 2])

    await AuthorCog.on_member_update(None, before, after)

    assert fake_redis.deleted_keys == ["user:discord:123"]


@pytest.mark.asyncio
async def test_unchanged_roles_keep_member_cache(monkeypatch):
    """成员资料变化但身份组不变时保留认证缓存。"""
    fake_redis = FakeRedis()
    monkeypatch.setattr(RedisManager, "get_client", lambda: fake_redis)
    before = SimpleNamespace(id=123, roles=[1])
    after = SimpleNamespace(id=123, roles=[1])

    await AuthorCog.on_member_update(None, before, after)

    assert fake_redis.deleted_keys == []
