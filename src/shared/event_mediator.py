import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

EventT = TypeVar("EventT")
ResultT = TypeVar("ResultT")
EventHandler = Callable[[Any], Awaitable[Any] | Any]


class EventMediator:
    """提供类型事件的可等待进程内发布与请求通信。"""

    def __init__(self) -> None:
        self._handlers: dict[type[object], list[EventHandler]] = defaultdict(list)

    def register(self, event_type: type[EventT], handler: EventHandler) -> None:
        """注册事件处理器并拒绝重复注册同一函数。"""
        handlers = self._handlers[event_type]
        if handler not in handlers:
            handlers.append(handler)

    async def publish(self, event: EventT) -> None:
        """按注册顺序等待完成指定类型事件的全部处理器。"""
        for handler in tuple(self._handlers[type(event)]):
            result = handler(event)
            if inspect.isawaitable(result):
                await result

    async def request(self, event: EventT) -> ResultT:
        """请求唯一处理器并等待其返回结果。"""
        handlers = self._handlers[type(event)]
        if len(handlers) != 1:
            raise RuntimeError(
                f"请求事件 {type(event).__name__} 必须恰有一个处理器，当前为 {len(handlers)} 个"
            )
        result = handlers[0](event)
        if inspect.isawaitable(result):
            result = await result
        return cast(ResultT, result)
