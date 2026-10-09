from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from api.v1.dependencies.security import get_current_user, require_auth
from api.v1.routers import author_follows
from models import Author, AuthorFollow
from shared.time_utils import utc_now


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_active", [None, True, False])
async def test_follow_response_after_commit(
    db_session_factory, monkeypatch, existing_active
):
    """真实过期会话下，首次、重复和重新关注均提交成功并返回可序列化响应。"""
    author_id = 9007199254740993
    user_id = 42
    previous_time = utc_now() - timedelta(days=1)
    assert db_session_factory.kw["expire_on_commit"] is True
    async with db_session_factory() as session, session.begin():
        session.add(Author(id=author_id, name="author", display_name="测试作者"))
        if existing_active is not None:
            session.add(
                AuthorFollow(
                    user_id=user_id,
                    author_id=author_id,
                    active_flag=existing_active,
                    followed_at=previous_time,
                )
            )

    app = FastAPI()
    app.include_router(author_follows.router, prefix="/v1")

    def current_user():
        """固定测试身份，隔离外部登录认证。"""
        return {"id": str(user_id)}

    app.dependency_overrides[require_auth] = current_user
    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(author_follows, "AsyncSessionFactory", db_session_factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post(f"/v1/author-follows/{author_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["author_id"] == str(author_id)
    assert body["active"] is True
    assert body["followed_at"].endswith("Z")
    # 使用独立会话确认实际落库结果，并核对重复关注不会重置时间。
    async with db_session_factory() as session:
        relation = (
            await session.execute(
                select(AuthorFollow).where(
                    AuthorFollow.user_id == user_id,
                    AuthorFollow.author_id == author_id,
                )
            )
        ).scalar_one()
        assert relation.active_flag is True
        if existing_active is True:
            assert relation.followed_at == previous_time
        else:
            assert relation.followed_at > previous_time
        expected = author_follows.AuthorFollowState(
            author_id=relation.author_id,
            followed_at=relation.followed_at,
            active=relation.active_flag,
        )
        assert body == expected.model_dump(mode="json")
