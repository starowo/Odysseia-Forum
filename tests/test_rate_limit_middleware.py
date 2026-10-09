"""测试 RateLimitMiddleware 的 body buffer-replay 机制。"""

import pytest

from api.middleware.rate_limit_middleware import RateLimitMiddleware


class TestReadAndReplayBody:
    """验证 _read_and_replay_body 的 ASGI 协议正确性。"""

    @pytest.mark.asyncio
    async def test_single_chunk_body(self):
        """单 chunk body — 最常见场景。"""
        body_data = b'{"include_authors":["123"]}'

        async def receive():
            return {"type": "http.request", "body": body_data, "more_body": False}

        body_bytes, replay_receive = await RateLimitMiddleware._read_and_replay_body(
            receive
        )

        assert body_bytes == body_data

        # replay 第一次调用应返回完整 body
        msg = await replay_receive()
        assert msg["type"] == "http.request"
        assert msg["body"] == body_data
        assert msg["more_body"] is False

    @pytest.mark.asyncio
    async def test_multi_chunk_body(self):
        """多 chunk body — 模拟大请求体分片传输。"""
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        calls = [0]

        async def receive():
            idx = calls[0]
            calls[0] += 1
            more = idx < len(chunks) - 1
            return {
                "type": "http.request",
                "body": chunks[idx],
                "more_body": more,
            }

        body_bytes, replay_receive = await RateLimitMiddleware._read_and_replay_body(
            receive
        )

        # 所有 chunk 拼接完整
        assert body_bytes == b"chunk1chunk2chunk3"

        # replay 返回完整拼接后的 body
        msg = await replay_receive()
        assert msg["body"] == b"chunk1chunk2chunk3"
        assert msg["more_body"] is False

    @pytest.mark.asyncio
    async def test_empty_body(self):
        """空 body — GET 请求之类。"""

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        body_bytes, replay_receive = await RateLimitMiddleware._read_and_replay_body(
            receive
        )

        assert body_bytes == b""
        msg = await replay_receive()
        assert msg["body"] == b""

    @pytest.mark.asyncio
    async def test_replay_then_original(self):
        """replay 首次调用返回 body，后续代理到原始 receive。"""
        calls = [0]

        async def receive():
            calls[0] += 1
            if calls[0] == 1:
                # 第一次：返回 body（被 _read_and_replay_body 消费）
                return {"type": "http.request", "body": b"test", "more_body": False}
            # 后续：返回 disconnect（模拟连接关闭）
            return {"type": "http.disconnect"}

        body_bytes, replay_receive = await RateLimitMiddleware._read_and_replay_body(
            receive
        )
        assert body_bytes == b"test"

        # 第一次 replay → 返回缓冲的 http.request
        msg1 = await replay_receive()
        assert msg1["type"] == "http.request"
        assert msg1["body"] == b"test"

        # 第二次 → 代理到原始 receive（返回 disconnect）
        msg2 = await replay_receive()
        assert msg2["type"] == "http.disconnect"
        assert calls[0] == 2  # 原始 receive 被调用了 2 次

    @pytest.mark.asyncio
    async def test_truncate_body(self):
        """body 截断逻辑。"""
        # 空 body
        assert RateLimitMiddleware._truncate_body(b"") == "-"

        # 短 body
        assert RateLimitMiddleware._truncate_body(b"hello") == "hello"

        # 超长 body 截断
        long_body = b"x" * 1200
        result = RateLimitMiddleware._truncate_body(long_body)
        assert len(result) == 1024

        # 中文 body
        cn_body = "你好世界".encode("utf-8")
        assert RateLimitMiddleware._truncate_body(cn_body) == "你好世界"

        long_cn_body = ("界" * 1100).encode("utf-8")
        assert len(RateLimitMiddleware._truncate_body(long_cn_body)) == 1024
