"""add user update preference table

Revision ID: add_user_update_pref
Revises: add_multi_server
Create Date: 2026-03-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "add_user_update_pref"
down_revision = "add_multi_server"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_update_preference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("auto_sync", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("no_remind", sa.Boolean(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_user_update_preference_user_id",
        "user_update_preference",
        ["user_id"],
    )
    op.create_index(
        "ix_user_update_preference_thread_id",
        "user_update_preference",
        ["thread_id"],
    )
    op.create_index(
        "uk_user_thread_update_pref",
        "user_update_preference",
        ["user_id", "thread_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uk_user_thread_update_pref", table_name="user_update_preference")
    op.drop_index(
        "ix_user_update_preference_thread_id", table_name="user_update_preference"
    )
    op.drop_index(
        "ix_user_update_preference_user_id", table_name="user_update_preference"
    )
    op.drop_table("user_update_preference")
