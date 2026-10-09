"""add content update, author follow and notification tables

Revision ID: add_content_update_notifications
Revises: add_thread_tag_reverse_index
Create Date: 2026-08-26 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.mock import MockConnection


revision: str = "add_content_update_notifications"
down_revision: Union[str, Sequence[str], None] = "add_thread_tag_reverse_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
_offline_assume_exists = False


def _is_offline_mode() -> bool:
    """判断迁移是否正在离线 SQL 生成模式运行。"""
    return isinstance(op.get_bind(), MockConnection)


def _has_table(table_name: str) -> bool:
    """判断当前 schema 是否存在指定表。"""
    if _is_offline_mode():
        return _offline_assume_exists
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    """判断指定表是否存在目标列。"""
    if _is_offline_mode():
        return _offline_assume_exists
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _has_index(table_name: str, index_name: str) -> bool:
    """判断指定表是否存在目标索引。"""
    if _is_offline_mode():
        return _offline_assume_exists
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    """判断指定表是否存在目标唯一约束。"""
    if _is_offline_mode():
        return _offline_assume_exists
    constraints = sa.inspect(op.get_bind()).get_unique_constraints(table_name)
    return any(constraint["name"] == constraint_name for constraint in constraints)


def _has_check_constraint(table_name: str, constraint_name: str) -> bool:
    """判断指定表是否存在目标检查约束。"""
    if _is_offline_mode():
        return _offline_assume_exists
    constraints = sa.inspect(op.get_bind()).get_check_constraints(table_name)
    return any(constraint["name"] == constraint_name for constraint in constraints)


def _column_is_nullable(table_name: str, column_name: str) -> bool:
    """判断指定列当前是否允许空值。"""
    if _is_offline_mode():
        return _offline_assume_exists
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    column = next(item for item in columns if item["name"] == column_name)
    return bool(column["nullable"])


def _ensure_index(
    table_name: str,
    index_name: str,
    columns: list[str],
    **kwargs: object,
) -> None:
    """仅在索引缺失时创建目标索引。"""
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns, **kwargs)


def _ensure_author_follow_schema() -> None:
    """创建或补齐作者关注表结构。"""
    if not _has_table("author_follow"):
        op.create_table(
            "author_follow",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("author_id", sa.BigInteger(), nullable=False),
            sa.Column("followed_at", sa.DateTime(), nullable=False),
            sa.Column(
                "active_flag",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.UniqueConstraint(
                "user_id",
                "author_id",
                name="uk_author_follow_user_author",
            ),
            sa.CheckConstraint(
                "user_id <> author_id",
                name="ck_author_follow_not_self",
            ),
        )
    else:
        # create_all 创建的表缺少数据库端布尔默认值，需要在此补齐
        op.alter_column(
            "author_follow",
            "active_flag",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.true(),
        )
        if not _has_unique_constraint("author_follow", "uk_author_follow_user_author"):
            op.create_unique_constraint(
                "uk_author_follow_user_author",
                "author_follow",
                ["user_id", "author_id"],
            )
        if not _has_check_constraint("author_follow", "ck_author_follow_not_self"):
            op.create_check_constraint(
                "ck_author_follow_not_self",
                "author_follow",
                "user_id <> author_id",
            )

    _ensure_index(
        "author_follow",
        "ix_author_follow_author_active_user",
        ["author_id", "active_flag", "user_id"],
    )
    _ensure_index(
        "author_follow",
        "ix_author_follow_user_active_followed",
        ["user_id", "active_flag", "followed_at"],
    )


def _ensure_thread_update_schema() -> None:
    """创建或补齐作品更新历史表结构。"""
    if not _has_table("thread_update"):
        op.create_table(
            "thread_update",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("thread_id", sa.BigInteger(), nullable=False),
            sa.Column("message_id", sa.BigInteger(), nullable=True),
            sa.Column("publisher_id", sa.BigInteger(), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("version", sa.String(length=50), nullable=True),
            sa.Column("source_message_at", sa.DateTime(), nullable=False),
            sa.Column("published_at", sa.DateTime(), nullable=False),
            sa.Column("overview_message_id", sa.BigInteger(), nullable=True),
            sa.UniqueConstraint("message_id", name="uk_thread_update_message"),
            sa.UniqueConstraint(
                "overview_message_id",
                name="uk_thread_update_overview_message",
            ),
            sa.CheckConstraint(
                "char_length(btrim(description)) BETWEEN 1 AND 500",
                name="ck_thread_update_description_length",
            ),
            sa.CheckConstraint(
                "version IS NULL OR char_length(btrim(version)) BETWEEN 1 AND 50",
                name="ck_thread_update_version_length",
            ),
        )
    else:
        if not _has_unique_constraint("thread_update", "uk_thread_update_message"):
            op.create_unique_constraint(
                "uk_thread_update_message",
                "thread_update",
                ["message_id"],
            )
        if not _has_unique_constraint(
            "thread_update", "uk_thread_update_overview_message"
        ):
            op.create_unique_constraint(
                "uk_thread_update_overview_message",
                "thread_update",
                ["overview_message_id"],
            )
        if not _has_check_constraint(
            "thread_update", "ck_thread_update_description_length"
        ):
            op.create_check_constraint(
                "ck_thread_update_description_length",
                "thread_update",
                "char_length(btrim(description)) BETWEEN 1 AND 500",
            )
        if not _has_check_constraint(
            "thread_update", "ck_thread_update_version_length"
        ):
            op.create_check_constraint(
                "ck_thread_update_version_length",
                "thread_update",
                "version IS NULL OR char_length(btrim(version)) BETWEEN 1 AND 50",
            )

    _ensure_index(
        "thread_update",
        "ix_thread_update_thread_published",
        ["thread_id", "published_at", "id"],
    )
    _ensure_index(
        "thread_update",
        "ix_thread_update_publisher_published",
        ["publisher_id", "published_at"],
    )


def _ensure_notification_schema() -> None:
    """创建或补齐统一动态通知表结构。"""
    if not _has_table("notification"):
        op.create_table(
            "notification",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("event_type", sa.String(length=32), nullable=False),
            sa.Column("event_source_id", sa.BigInteger(), nullable=False),
            sa.Column("thread_id", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "user_id",
                "event_type",
                "event_source_id",
                name="uk_notification_user_event_source",
            ),
            sa.CheckConstraint(
                "event_type IN ('thread_update', 'author_new_thread')",
                name="ck_notification_event_type",
            ),
        )
    else:
        if not _has_unique_constraint(
            "notification", "uk_notification_user_event_source"
        ):
            op.create_unique_constraint(
                "uk_notification_user_event_source",
                "notification",
                ["user_id", "event_type", "event_source_id"],
            )
        if not _has_check_constraint("notification", "ck_notification_event_type"):
            op.create_check_constraint(
                "ck_notification_event_type",
                "notification",
                "event_type IN ('thread_update', 'author_new_thread')",
            )

    _ensure_index(
        "notification",
        "ix_notification_user_created",
        ["user_id", "created_at", "id"],
    )
    _ensure_index(
        "notification",
        "ix_notification_event_source",
        ["event_type", "event_source_id"],
    )
    _ensure_index(
        "notification",
        "ix_notification_unread_user",
        ["user_id", "created_at"],
        postgresql_where=sa.text("read_at IS NULL"),
    )
    _ensure_index(
        "notification",
        "ix_notification_unread_user_thread",
        ["user_id", "thread_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )


def _ensure_thread_projection_schema() -> None:
    """补齐帖子最新更新投影列及索引。"""
    if not _has_column("thread", "latest_update_id"):
        op.add_column(
            "thread",
            sa.Column("latest_update_id", sa.Integer(), nullable=True),
        )
    _ensure_index(
        "thread",
        "ix_thread_latest_update_id",
        ["latest_update_id"],
    )


def _ensure_banner_cover_schema() -> None:
    """放宽帖子 Banner 图片字段并补齐频道图片约束。"""
    for table_name in (
        "banner_application",
        "banner_carousel",
        "banner_waitlist",
    ):
        if not _column_is_nullable(table_name, "cover_image_url"):
            op.alter_column(
                table_name,
                "cover_image_url",
                existing_type=sa.String(),
                nullable=True,
            )
        constraint_name = f"ck_{table_name}_channel_cover"
        if not _has_check_constraint(table_name, constraint_name):
            op.create_check_constraint(
                constraint_name,
                table_name,
                "target_type <> 2 OR cover_image_url IS NOT NULL",
            )


def _ensure_thread_follow_unique_constraint() -> None:
    """合并历史重复关注并补齐帖子关注唯一约束。"""
    if _has_unique_constraint("thread_follow", "uk_thread_follow_user_thread"):
        return

    # 在添加唯一约束前合并可能存在的历史重复关注记录
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                first_value(id) OVER (
                    PARTITION BY user_id, thread_id
                    ORDER BY id
                ) AS keep_id,
                bool_or(active_flag) OVER (
                    PARTITION BY user_id, thread_id
                ) AS merged_active,
                max(followed_at) OVER (
                    PARTITION BY user_id, thread_id
                ) AS merged_followed_at,
                max(last_viewed_at) OVER (
                    PARTITION BY user_id, thread_id
                ) AS merged_last_viewed_at
            FROM thread_follow
        ), updated AS (
            UPDATE thread_follow AS target
            SET active_flag = ranked.merged_active,
                followed_at = ranked.merged_followed_at,
                last_viewed_at = ranked.merged_last_viewed_at
            FROM ranked
            WHERE target.id = ranked.keep_id
            RETURNING target.id
        )
        DELETE FROM thread_follow AS duplicate
        USING ranked
        WHERE duplicate.id = ranked.id
          AND ranked.id <> ranked.keep_id
        """
    )
    op.create_unique_constraint(
        "uk_thread_follow_user_thread",
        "thread_follow",
        ["user_id", "thread_id"],
    )


def _ensure_update_preference_constraint() -> None:
    """修正冲突偏好并补齐互斥检查约束。"""
    # 重复执行该修正不会改变已经合法的数据
    op.execute(
        """
        UPDATE user_update_preference
        SET auto_sync = false
        WHERE auto_sync = true AND no_remind = true
        """
    )
    if not _has_check_constraint(
        "user_update_preference", "ck_user_update_preference_exclusive"
    ):
        op.create_check_constraint(
            "ck_user_update_preference_exclusive",
            "user_update_preference",
            "NOT (auto_sync AND no_remind)",
        )


def upgrade() -> None:
    """幂等补齐动态通知数据结构并放宽帖子 Banner 图片约束。"""
    global _offline_assume_exists
    _offline_assume_exists = False
    _ensure_author_follow_schema()
    _ensure_thread_update_schema()
    _ensure_thread_projection_schema()
    _ensure_notification_schema()
    _ensure_banner_cover_schema()
    _ensure_thread_follow_unique_constraint()
    _ensure_update_preference_constraint()


def downgrade() -> None:
    """幂等移除动态通知结构并恢复旧 Banner 非空约束。"""
    global _offline_assume_exists
    _offline_assume_exists = True
    # 恢复现有表约束
    if _has_check_constraint(
        "user_update_preference", "ck_user_update_preference_exclusive"
    ):
        op.drop_constraint(
            "ck_user_update_preference_exclusive",
            "user_update_preference",
            type_="check",
        )
    if _has_unique_constraint("thread_follow", "uk_thread_follow_user_thread"):
        op.drop_constraint(
            "uk_thread_follow_user_thread",
            "thread_follow",
            type_="unique",
        )

    # 删除频道图片约束并恢复非空字段
    for table in ("banner_application", "banner_carousel", "banner_waitlist"):
        constraint_name = f"ck_{table}_channel_cover"
        if _has_check_constraint(table, constraint_name):
            op.drop_constraint(
                constraint_name,
                table,
                type_="check",
            )
        op.execute(
            f"UPDATE {table} SET cover_image_url = '' WHERE cover_image_url IS NULL"
        )
        if _column_is_nullable(table, "cover_image_url"):
            op.alter_column(
                table,
                "cover_image_url",
                existing_type=sa.String(),
                nullable=False,
            )

    # 删除新增通知与更新结构
    if _has_table("notification"):
        op.drop_table("notification")
    if _has_index("thread", "ix_thread_latest_update_id"):
        op.drop_index("ix_thread_latest_update_id", table_name="thread")
    if _has_column("thread", "latest_update_id"):
        op.drop_column("thread", "latest_update_id")
    if _has_table("thread_update"):
        op.drop_table("thread_update")
    if _has_table("author_follow"):
        op.drop_table("author_follow")
