from models.tag_notification_task import TagNotificationTask

from sqlalchemy.exc import IntegrityError

from core.tag_pool_cache_service import TagPoolCacheService
from dto.events.tag_command import TagCommand
from shared.event_mediator import EventMediator
from shared.tag_error import TagError
from tag.custom_tag_service import CustomTagService


def create_tag_mediator(session_factory, config, redis_client=None) -> EventMediator:
    """在程序组装入口注册标签事件，避免业务模块直接相互导入。"""
    mediator = EventMediator()
    pool_cache = TagPoolCacheService(redis_client)

    async def handle(command):
        """在独立事务中处理事件并返回脱离会话的数据。"""
        try:
            # 高频完整标签池优先读取 Redis，命中时不占用数据库连接。
            if command.action == "pool":
                cached = await pool_cache.get(command.payload)
                if cached is not None:
                    return cached
            async with session_factory() as session, session.begin():
                result = await CustomTagService(session, config).dispatch(command)
                # 在共享事务锁释放前回填，后续写事务提交后会统一失效。
                if command.action == "pool":
                    await pool_cache.set(command.payload, result)
            if command.action == "manage" or (
                command.action == "merge" and not command.payload.get("preview")
            ):
                await pool_cache.invalidate()
            return result
        except TagError as exc:
            conflict_id = exc.detail.get("conflict_tag_id")
            if conflict_id:
                async with session_factory() as session, session.begin():
                    session.add(
                        TagNotificationTask(kind="conflict", tag_id=int(conflict_id))
                    )
            raise
        except IntegrityError as exc:
            raise TagError("concurrent_conflict", "数据已变化，请刷新后重试") from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise TagError(
                "invalid_request", "缺少操作所需参数或参数格式错误", 422
            ) from exc

    mediator.register(TagCommand, handle)
    return mediator
