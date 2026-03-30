"""add multi-server support

Revision ID: add_multi_server
Revises: 3f8f2d284f85
Create Date: 2026-03-09 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "add_multi_server"
down_revision = "3f8f2d284f85"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 为 thread 表添加 guild_id 列
    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "guild_id",
                sa.BigInteger(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.create_index("ix_thread_guild_id", ["guild_id"])

    # 清除 server_default (仅作迁移用途)
    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.alter_column("guild_id", server_default=None)

    # 2. 重建 usersearchpreferences 表：用原始 SQL 手动处理
    #    SQLite 不支持 ALTER 主键，且 Alembic batch 模式在新增 NOT NULL 自增列时
    #    无法自动填充已有行，所以直接用 SQL 重建。
    op.execute(sa.text("""
        CREATE TABLE _new_usersearchpreferences (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            user_id BIGINT NOT NULL,
            guild_id BIGINT NOT NULL DEFAULT 0,
            preferred_channels JSON,
            include_authors JSON,
            exclude_authors JSON,
            created_after VARCHAR,
            created_before VARCHAR,
            active_after VARCHAR,
            active_before VARCHAR,
            include_tags JSON,
            exclude_tags JSON,
            include_keywords VARCHAR NOT NULL DEFAULT '',
            exclude_keywords VARCHAR NOT NULL DEFAULT '',
            exclude_keyword_exemption_markers JSON,
            preview_image_mode VARCHAR NOT NULL DEFAULT 'thumbnail',
            results_per_page INTEGER NOT NULL DEFAULT 5,
            sort_method VARCHAR NOT NULL DEFAULT 'comprehensive',
            custom_base_sort VARCHAR NOT NULL DEFAULT 'comprehensive'
        )
    """))

    op.execute(sa.text("""
        INSERT INTO _new_usersearchpreferences (
            user_id, guild_id, preferred_channels,
            include_authors, exclude_authors,
            created_after, created_before, active_after, active_before,
            include_tags, exclude_tags,
            include_keywords, exclude_keywords, exclude_keyword_exemption_markers,
            preview_image_mode, results_per_page,
            sort_method, custom_base_sort
        )
        SELECT
            user_id, 0, preferred_channels,
            include_authors, exclude_authors,
            created_after, created_before, active_after, active_before,
            include_tags, exclude_tags,
            COALESCE(include_keywords, ''), COALESCE(exclude_keywords, ''),
            exclude_keyword_exemption_markers,
            COALESCE(preview_image_mode, 'thumbnail'), COALESCE(results_per_page, 5),
            COALESCE(sort_method, 'comprehensive'), COALESCE(custom_base_sort, 'comprehensive')
        FROM usersearchpreferences
    """))

    op.execute(sa.text("DROP TABLE usersearchpreferences"))
    op.execute(sa.text(
        "ALTER TABLE _new_usersearchpreferences RENAME TO usersearchpreferences"
    ))

    # 创建索引和唯一约束
    op.create_index(
        "ix_usersearchpreferences_user_id",
        "usersearchpreferences",
        ["user_id"],
    )
    op.create_index(
        "ix_usersearchpreferences_guild_id",
        "usersearchpreferences",
        ["guild_id"],
    )
    op.create_index(
        "uq_user_guild_preferences",
        "usersearchpreferences",
        ["user_id", "guild_id"],
        unique=True,
    )


def downgrade() -> None:
    # 重建 usersearchpreferences 恢复旧结构（user_id 做主键）
    op.drop_index("uq_user_guild_preferences", table_name="usersearchpreferences")
    op.drop_index("ix_usersearchpreferences_guild_id", table_name="usersearchpreferences")
    op.drop_index("ix_usersearchpreferences_user_id", table_name="usersearchpreferences")

    op.execute(sa.text("""
        CREATE TABLE _old_usersearchpreferences (
            user_id BIGINT NOT NULL PRIMARY KEY,
            preferred_channels JSON,
            include_authors JSON,
            exclude_authors JSON,
            created_after VARCHAR,
            created_before VARCHAR,
            active_after VARCHAR,
            active_before VARCHAR,
            include_tags JSON,
            exclude_tags JSON,
            include_keywords VARCHAR NOT NULL DEFAULT '',
            exclude_keywords VARCHAR NOT NULL DEFAULT '',
            exclude_keyword_exemption_markers JSON,
            preview_image_mode VARCHAR NOT NULL DEFAULT 'thumbnail',
            results_per_page INTEGER NOT NULL DEFAULT 5,
            sort_method VARCHAR NOT NULL DEFAULT 'comprehensive',
            custom_base_sort VARCHAR NOT NULL DEFAULT 'comprehensive'
        )
    """))

    op.execute(sa.text("""
        INSERT OR IGNORE INTO _old_usersearchpreferences
        SELECT user_id, preferred_channels,
            include_authors, exclude_authors,
            created_after, created_before, active_after, active_before,
            include_tags, exclude_tags,
            include_keywords, exclude_keywords, exclude_keyword_exemption_markers,
            preview_image_mode, results_per_page,
            sort_method, custom_base_sort
        FROM usersearchpreferences
    """))

    op.execute(sa.text("DROP TABLE usersearchpreferences"))
    op.execute(sa.text(
        "ALTER TABLE _old_usersearchpreferences RENAME TO usersearchpreferences"
    ))

    # 移除 thread 表的 guild_id 列
    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.drop_index("ix_thread_guild_id")
        batch_op.drop_column("guild_id")
