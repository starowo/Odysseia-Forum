"""add booklist_publish table and publish_status to booklist

Revision ID: add_booklist_publish_table
Revises: set_table_storage_params
Create Date: 2026-07-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_booklist_publish_table"
down_revision: Union[str, None] = "set_table_storage_params"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 booklist_publish 表
    op.create_table(
        "booklist_publish",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("booklist_id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("message_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "booklist_id", "thread_id", name="uq_booklist_publish_thread"
        ),
    )
    op.create_index(
        "ix_booklist_publish_booklist_id",
        "booklist_publish",
        ["booklist_id"],
    )
    op.create_index(
        "ix_booklist_publish_thread_id",
        "booklist_publish",
        ["thread_id"],
    )

    # 在 booklist 表添加 publish_status 列
    op.add_column(
        "booklist",
        sa.Column(
            "publish_status",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index(
        "ix_booklist_publish_status",
        "booklist",
        ["publish_status"],
    )


def downgrade() -> None:
    # 移除 publish_status 列
    op.drop_index("ix_booklist_publish_status", table_name="booklist")
    op.drop_column("booklist", "publish_status")

    # 删除 booklist_publish 表
    op.drop_index("ix_booklist_publish_thread_id", table_name="booklist_publish")
    op.drop_index("ix_booklist_publish_booklist_id", table_name="booklist_publish")
    op.drop_table("booklist_publish")
