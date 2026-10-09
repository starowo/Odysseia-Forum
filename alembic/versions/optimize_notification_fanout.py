"""optimize notification fanout

Revision ID: optimize_notification_fanout
Revises: add_content_update_notifications
Create Date: 2026-08-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.mock import MockConnection


revision: str = "optimize_notification_fanout"
down_revision: Union[str, Sequence[str], None] = "add_content_update_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_offline_mode() -> bool:
    """判断迁移是否正在离线 SQL 生成模式运行。"""
    return isinstance(op.get_bind(), MockConnection)


def upgrade() -> None:
    """幂等添加帖子关注通知扇出普通复合索引。"""
    index_exists = False
    if not _is_offline_mode():
        indexes = sa.inspect(op.get_bind()).get_indexes("thread_follow")
        index_exists = any(
            index["name"] == "ix_thread_follow_thread_active_user" for index in indexes
        )
    if not index_exists:
        op.create_index(
            "ix_thread_follow_thread_active_user",
            "thread_follow",
            ["thread_id", "active_flag", "user_id"],
        )


def downgrade() -> None:
    """幂等移除帖子关注通知扇出复合索引。"""
    index_exists = True
    if not _is_offline_mode():
        indexes = sa.inspect(op.get_bind()).get_indexes("thread_follow")
        index_exists = any(
            index["name"] == "ix_thread_follow_thread_active_user" for index in indexes
        )
    if index_exists:
        op.drop_index(
            "ix_thread_follow_thread_active_user",
            table_name="thread_follow",
        )
