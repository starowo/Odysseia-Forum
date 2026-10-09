"""add active_flag to thread_follow

Revision ID: add_thread_follow_active_flag
Revises: baseline_pg
Create Date: 2026-06-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_thread_follow_active_flag"
down_revision: Union[str, Sequence[str], None] = "baseline_pg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "thread_follow",
        sa.Column(
            "active_flag",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_index(
        "ix_thread_follow_active_flag",
        "thread_follow",
        ["active_flag"],
    )


def downgrade() -> None:
    op.drop_index("ix_thread_follow_active_flag")
    op.drop_column("thread_follow", "active_flag")
