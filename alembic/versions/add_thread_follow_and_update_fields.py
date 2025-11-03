"""add thread follow and update fields

Revision ID: add_thread_follow_update
Revises: cad7c31b4443
Create Date: 2025-11-05 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_thread_follow_update"
down_revision = "cad7c31b4443"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 thread_follow 表
    op.create_table(
        "thread_follow",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("followed_at", sa.DateTime(), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 为 thread_follow 创建索引
    op.create_index("ix_thread_follow_user_id", "thread_follow", ["user_id"])
    op.create_index("ix_thread_follow_thread_id", "thread_follow", ["thread_id"])
    op.create_index(
        "ix_thread_follow_user_thread",
        "thread_follow",
        ["user_id", "thread_id"],
        unique=True,
    )

    # 为 thread 表添加更新相关字段
    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.add_column(sa.Column("latest_update_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("latest_update_link", sa.String(), nullable=True))
        batch_op.create_index("ix_thread_latest_update_at", ["latest_update_at"])


def downgrade() -> None:
    # 删除 thread 表的更新相关字段
    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.drop_index("ix_thread_latest_update_at")
        batch_op.drop_column("latest_update_link")
        batch_op.drop_column("latest_update_at")

    # 删除 thread_follow 表的索引
    op.drop_index("ix_thread_follow_user_thread", table_name="thread_follow")
    op.drop_index("ix_thread_follow_thread_id", table_name="thread_follow")
    op.drop_index("ix_thread_follow_user_id", table_name="thread_follow")

    # 删除 thread_follow 表
    op.drop_table("thread_follow")
