from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.author_follow_repository import AuthorFollowRepository
from core.notification_fanout_service import NotificationFanoutService
from core.notification_repository import NotificationRepository
from core.thread_update_service import ThreadUpdateError, ThreadUpdateService
from core.viewer_flag_service import ViewerFlagService
from models import (
    AuthorFollow,
    Notification,
    Thread,
    ThreadFollow,
    ThreadUpdate,
    UserCollection,
)
from shared.enum import CollectionType
from shared.time_utils import utc_now


@pytest.mark.asyncio
async def test_publish_update_is_atomic_idempotent_and_excludes_author(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """发布更新同时维护历史、投影和关注者通知。"""
    async with db_session_factory() as session:
        session.add(
            Thread(
                guild_id=10,
                channel_id=20,
                thread_id=30,
                title="测试作品",
                author_id=40,
                created_at=utc_now() - timedelta(days=2),
            )
        )
        session.add_all(
            [
                ThreadFollow(user_id=40, thread_id=30),
                ThreadFollow(user_id=41, thread_id=30),
                ThreadFollow(user_id=42, thread_id=30, active_flag=False),
            ]
        )
        await session.commit()

    service = ThreadUpdateService(db_session_factory)
    published = await service.publish(
        thread_id=30,
        message_id=50,
        publisher_id=40,
        description="  系统自动同步  ",
        version=None,
        source_message_at=utc_now(),
    )

    async with db_session_factory() as session:
        thread = (
            await session.execute(select(Thread).where(Thread.thread_id == 30))
        ).scalar_one()
        notifications = list(
            (
                await session.execute(
                    select(Notification).where(Notification.thread_id == 30)
                )
            )
            .scalars()
            .all()
        )
        assert thread.latest_update_id == published.id
        assert thread.latest_update_link.endswith("/30/50")
        assert [item.user_id for item in notifications] == [41]
        assert published.description == "系统自动同步"

    with pytest.raises(ThreadUpdateError, match="已经发布"):
        await service.publish(
            thread_id=30,
            message_id=50,
            publisher_id=40,
            description="重复",
            version=None,
            source_message_at=utc_now(),
        )


@pytest.mark.asyncio
async def test_publish_update_fans_out_beyond_asyncpg_parameter_limit(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """大量关注者通知通过数据库内扇出避免绑定参数数量限制。"""
    follower_count = 6000
    thread_id = 3000
    publisher_id = 4000
    async with db_session_factory() as session:
        session.add(
            Thread(
                guild_id=1000,
                channel_id=2000,
                thread_id=thread_id,
                title="大规模扇出测试",
                author_id=publisher_id,
                created_at=utc_now() - timedelta(days=2),
            )
        )
        session.add_all(
            [
                ThreadFollow(
                    user_id=100_000 + offset,
                    thread_id=thread_id,
                )
                for offset in range(follower_count)
            ]
        )
        session.add(
            ThreadFollow(
                user_id=999_999,
                thread_id=thread_id,
                active_flag=False,
            )
        )
        await session.commit()

    await ThreadUpdateService(db_session_factory).publish(
        thread_id=thread_id,
        message_id=5000,
        publisher_id=publisher_id,
        description="系统自动同步",
        version=None,
        source_message_at=utc_now(),
    )

    async with db_session_factory() as session:
        notification_count = (
            await session.execute(
                select(func.count())
                .select_from(Notification)
                .where(Notification.thread_id == thread_id)
            )
        ).scalar_one()
        assert notification_count == follower_count


@pytest.mark.asyncio
async def test_author_new_thread_fanout_is_idempotent_and_filters_followers(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """作者新作品仅通知活跃关注者并通过唯一约束保持幂等。"""
    async with db_session_factory() as session:
        session.add_all(
            [
                AuthorFollow(user_id=7001, author_id=7000),
                AuthorFollow(user_id=7002, author_id=7000),
                AuthorFollow(user_id=7003, author_id=7000, active_flag=False),
            ]
        )
        await session.flush()

        fanout_service = NotificationFanoutService(session)
        first_count = await fanout_service.fanout_author_new_thread(
            author_id=7000,
            thread_id=8000,
            event_source_id=8000,
        )
        duplicate_count = await fanout_service.fanout_author_new_thread(
            author_id=7000,
            thread_id=8000,
            event_source_id=8000,
        )
        await session.commit()

    async with db_session_factory() as session:
        recipient_ids = list(
            (
                await session.execute(
                    select(Notification.user_id).where(
                        Notification.event_type == "author_new_thread",
                        Notification.event_source_id == 8000,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert first_count == 2
        assert duplicate_count == 0
        assert sorted(recipient_ids) == [7001, 7002]


@pytest.mark.asyncio
async def test_publish_update_rolls_back_when_fanout_fails(
    db_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """通知扇出失败时回滚更新历史和帖子最新投影。"""
    thread_id = 9000
    publisher_id = 9001
    async with db_session_factory() as session:
        session.add(
            Thread(
                guild_id=9002,
                channel_id=9003,
                thread_id=thread_id,
                title="事务回滚测试",
                author_id=publisher_id,
                created_at=utc_now() - timedelta(days=2),
            )
        )
        session.add(ThreadFollow(user_id=9004, thread_id=thread_id))
        await session.commit()

    async def fail_fanout(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("模拟通知扇出失败")

    monkeypatch.setattr(
        NotificationFanoutService,
        "fanout_thread_update",
        fail_fanout,
    )

    with pytest.raises(RuntimeError, match="模拟通知扇出失败"):
        await ThreadUpdateService(db_session_factory).publish(
            thread_id=thread_id,
            message_id=9005,
            publisher_id=publisher_id,
            description="系统自动同步",
            version=None,
            source_message_at=utc_now(),
        )

    async with db_session_factory() as session:
        thread = (
            await session.execute(select(Thread).where(Thread.thread_id == thread_id))
        ).scalar_one()
        update_count = (
            await session.execute(
                select(func.count())
                .select_from(ThreadUpdate)
                .where(ThreadUpdate.thread_id == thread_id)
            )
        ).scalar_one()
        notification_count = (
            await session.execute(
                select(func.count())
                .select_from(Notification)
                .where(Notification.thread_id == thread_id)
            )
        ).scalar_one()
        assert thread.latest_update_id is None
        assert thread.latest_update_at is None
        assert thread.latest_update_link is None
        assert update_count == 0
        assert notification_count == 0


@pytest.mark.asyncio
async def test_delete_latest_update_restores_previous_projection(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """删除最新发布时回滚投影并删除该次通知。"""
    async with db_session_factory() as session:
        session.add(
            Thread(
                guild_id=11,
                channel_id=21,
                thread_id=31,
                title="回滚测试",
                author_id=41,
                created_at=utc_now() - timedelta(days=2),
            )
        )
        session.add(ThreadFollow(user_id=99, thread_id=31))
        await session.commit()
    service = ThreadUpdateService(db_session_factory)
    first = await service.publish(
        31, 51, 41, "第一版", "v1", utc_now() - timedelta(hours=1)
    )
    second = await service.publish(31, 52, 41, "第二版", "v2", utc_now())

    await service.delete(second.id, 41)

    async with db_session_factory() as session:
        thread = (
            await session.execute(select(Thread).where(Thread.thread_id == 31))
        ).scalar_one()
        remaining_updates = list(
            (
                await session.execute(
                    select(ThreadUpdate).where(ThreadUpdate.thread_id == 31)
                )
            )
            .scalars()
            .all()
        )
        notification_sources = list(
            (
                await session.execute(
                    select(Notification.event_source_id).where(
                        Notification.thread_id == 31
                    )
                )
            )
            .scalars()
            .all()
        )
        assert thread.latest_update_id == first.id
        assert thread.latest_update_link.endswith("/31/51")
        assert [item.id for item in remaining_updates] == [first.id]
        assert notification_sources == [first.id]


@pytest.mark.asyncio
async def test_viewer_flags_and_thread_read_are_unified(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """四种查看者标记独立聚合且按作品统一已读。"""
    async with db_session_factory() as session:
        session.add(ThreadFollow(user_id=60, thread_id=70))
        session.add(
            UserCollection(
                user_id=60,
                target_type=CollectionType.THREAD.value,
                target_id=70,
            )
        )
        await AuthorFollowRepository(session).set_active(60, 80, True)
        session.add_all(
            [
                Notification(
                    user_id=60,
                    event_type="thread_update",
                    event_source_id=1,
                    thread_id=70,
                ),
                Notification(
                    user_id=60,
                    event_type="author_new_thread",
                    event_source_id=70,
                    thread_id=70,
                ),
            ]
        )
        await session.commit()

        flags = await ViewerFlagService(session).get_flags(60, [(70, 80)])
        assert flags.for_thread(70) == [
            "collected",
            "followed",
            "followed_author",
            "unread",
        ]
        marked = await NotificationRepository(session).mark_thread_read(60, 70)
        await session.commit()
        assert marked == 2
        flags = await ViewerFlagService(session).get_flags(60, [(70, 80)])
        assert flags.for_thread(70) == [
            "collected",
            "followed",
            "followed_author",
        ]


def test_new_business_tables_have_no_physical_foreign_keys() -> None:
    """新增业务表只使用逻辑 ID，不创建实体外键。"""
    assert not AuthorFollow.__table__.foreign_keys
    assert not ThreadUpdate.__table__.foreign_keys
    assert not Notification.__table__.foreign_keys
