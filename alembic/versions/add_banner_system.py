"""add banner system

Revision ID: add_banner_system
Revises: add_thread_follow_update
Create Date: 2025-11-06 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_banner_system"
down_revision = "add_thread_follow_update"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 banner_application 表
    op.create_table(
        "banner_application",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("applicant_id", sa.Integer(), nullable=False),
        sa.Column("cover_image_url", sa.String(), nullable=False),
        sa.Column("target_scope", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("reject_reason", sa.String(), nullable=True),
        sa.Column("review_message_id", sa.Integer(), nullable=True),
        sa.Column("review_thread_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 为 banner_application 创建索引
    op.create_index(
        "ix_banner_application_thread_id", "banner_application", ["thread_id"]
    )
    op.create_index(
        "ix_banner_application_channel_id", "banner_application", ["channel_id"]
    )
    op.create_index(
        "ix_banner_application_applicant_id", "banner_application", ["applicant_id"]
    )
    op.create_index(
        "ix_banner_application_target_scope", "banner_application", ["target_scope"]
    )
    op.create_index("ix_banner_application_status", "banner_application", ["status"])

    # 创建 banner_carousel 表
    op.create_table(
        "banner_carousel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=True),
        sa.Column("cover_image_url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 为 banner_carousel 创建索引
    op.create_index("ix_banner_carousel_thread_id", "banner_carousel", ["thread_id"])
    op.create_index("ix_banner_carousel_channel_id", "banner_carousel", ["channel_id"])
    op.create_index("ix_banner_carousel_start_time", "banner_carousel", ["start_time"])
    op.create_index("ix_banner_carousel_end_time", "banner_carousel", ["end_time"])
    op.create_index("ix_banner_carousel_position", "banner_carousel", ["position"])

    # 创建 banner_waitlist 表
    op.create_table(
        "banner_waitlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=True),
        sa.Column("cover_image_url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("queued_at", sa.DateTime(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 为 banner_waitlist 创建索引
    op.create_index("ix_banner_waitlist_thread_id", "banner_waitlist", ["thread_id"])
    op.create_index("ix_banner_waitlist_channel_id", "banner_waitlist", ["channel_id"])
    op.create_index("ix_banner_waitlist_queued_at", "banner_waitlist", ["queued_at"])
    op.create_index("ix_banner_waitlist_position", "banner_waitlist", ["position"])


def downgrade() -> None:
    # 删除 banner_waitlist 表的索引和表
    op.drop_index("ix_banner_waitlist_position", table_name="banner_waitlist")
    op.drop_index("ix_banner_waitlist_queued_at", table_name="banner_waitlist")
    op.drop_index("ix_banner_waitlist_channel_id", table_name="banner_waitlist")
    op.drop_index("ix_banner_waitlist_thread_id", table_name="banner_waitlist")
    op.drop_table("banner_waitlist")

    # 删除 banner_carousel 表的索引和表
    op.drop_index("ix_banner_carousel_position", table_name="banner_carousel")
    op.drop_index("ix_banner_carousel_end_time", table_name="banner_carousel")
    op.drop_index("ix_banner_carousel_start_time", table_name="banner_carousel")
    op.drop_index("ix_banner_carousel_channel_id", table_name="banner_carousel")
    op.drop_index("ix_banner_carousel_thread_id", table_name="banner_carousel")
    op.drop_table("banner_carousel")

    # 删除 banner_application 表的索引和表
    op.drop_index("ix_banner_application_status", table_name="banner_application")
    op.drop_index("ix_banner_application_target_scope", table_name="banner_application")
    op.drop_index("ix_banner_application_applicant_id", table_name="banner_application")
    op.drop_index("ix_banner_application_channel_id", table_name="banner_application")
    op.drop_index("ix_banner_application_thread_id", table_name="banner_application")
    op.drop_table("banner_application")
