from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.v1.routers import booklists
from api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData


MAX_ID = 9223372036854775807
PASTED_ID = 113455755301199884015482284250497065671548228425049706567
OVERFLOW_MESSAGE = (
    "帖子 ID 超出有效范围，请检查多个 ID 之间是否遗漏逗号，每个 ID 应单独提交。"
)
INVALID_MESSAGE = "帖子 ID 必须是有效的正整数。"


@pytest.mark.parametrize(
    "value", [1, "1", MAX_ID, str(MAX_ID), "000123", "0" * 5000 + "1"]
)
def test_valid_thread_id_is_normalized(value):
    """合法 ID 保持整数形式，前导零不影响范围判断。"""
    item = BooklistItemAddData(thread_id=value)
    assert type(item.thread_id) is int
    expected = int(value.lstrip("0")) if isinstance(value, str) else value
    assert item.thread_id == expected


@pytest.mark.parametrize(
    "value, message",
    [
        (v, OVERFLOW_MESSAGE)
        for v in [MAX_ID + 1, str(MAX_ID + 1), PASTED_ID, str(PASTED_ID), "9" * 5000]
    ]
    + [
        (v, INVALID_MESSAGE)
        for v in [
            0,
            "0",
            -1,
            "-1",
            True,
            False,
            1.0,
            1.5,
            None,
            "",
            "abc",
            "1,2",
            " ",
            [],
            {},
            "²",
        ]
    ],
)
def test_invalid_thread_id_has_chinese_message(value, message):
    """非法类型与越界 ID 返回对应中文提示。"""
    with pytest.raises(ValidationError) as exc_info:
        BooklistItemAddData(thread_id=value)
    error = exc_info.value.errors()[0]
    assert error["loc"] == ("thread_id",)
    assert message in error["msg"]


@pytest.mark.parametrize("value", [PASTED_ID, str(PASTED_ID), "9" * 5000])
def test_invalid_batch_returns_422_before_service(monkeypatch, value):
    """混合批次定位非法条目并在创建会话和调用服务之前拒绝请求。"""
    # 使用真实路由并替换鉴权，避免测试依赖外部服务。
    app = FastAPI()
    app.include_router(booklists.router)
    app.dependency_overrides[booklists.require_auth] = lambda: {"id": "123"}
    session_factory = MagicMock()
    service = MagicMock()
    monkeypatch.setattr(booklists, "AsyncSessionFactory", session_factory)
    monkeypatch.setattr(booklists, "BooklistService", service)

    with TestClient(app) as client:
        response = client.post(
            "/booklist/item/add/7005",
            json={"items": [{"thread_id": "1001"}, {"thread_id": value}]},
        )

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "items", 1, "thread_id"]
    assert OVERFLOW_MESSAGE in error["msg"]
    session_factory.assert_not_called()
    service.assert_not_called()
