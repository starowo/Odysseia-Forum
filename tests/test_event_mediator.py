from dataclasses import dataclass

import pytest

from shared.event_mediator import EventMediator


@dataclass(frozen=True)
class ExampleRequest:
    """测试请求事件。"""

    value: int


@pytest.mark.asyncio
async def test_request_requires_exactly_one_handler() -> None:
    """请求事件只有唯一处理器时才能返回结果。"""
    mediator = EventMediator()
    with pytest.raises(RuntimeError, match="恰有一个"):
        await mediator.request(ExampleRequest(1))

    async def handler(event: ExampleRequest) -> int:
        return event.value + 1

    mediator.register(ExampleRequest, handler)
    assert await mediator.request(ExampleRequest(1)) == 2

    mediator.register(ExampleRequest, lambda event: event.value)
    with pytest.raises(RuntimeError, match="当前为 2 个"):
        await mediator.request(ExampleRequest(1))
