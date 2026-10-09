"""add channel table and target_type to banner tables

Revision ID: add_channel_table
Revises: add_thread_follow_active_flag
Create Date: 2026-06-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_channel_table"
down_revision: Union[str, Sequence[str], None] = "add_thread_follow_active_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 channel 表
    op.create_table(
        "channel",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "channel_id",
            sa.BigInteger(),
            unique=True,
            index=True,
            nullable=False,
        ),
        sa.Column("guild_id", sa.BigInteger(), index=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # banner 三张表加 target_type
    for table in ("banner_application", "banner_carousel", "banner_waitlist"):
        op.add_column(
            table,
            sa.Column(
                "target_type",
                sa.SmallInteger(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )
        op.create_index(f"ix_{table}_target_type", table, ["target_type"])


def downgrade() -> None:
    for table in ("banner_application", "banner_carousel", "banner_waitlist"):
        op.drop_index(f"ix_{table}_target_type")
        op.drop_column(table, "target_type")
    op.drop_table("channel")
