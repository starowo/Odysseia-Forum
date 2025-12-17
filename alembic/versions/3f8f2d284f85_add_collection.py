"""add collection

Revision ID: 3f8f2d284f85
Revises: add_thumbnail_urls_list
Create Date: 2025-12-11 20:36:21.187532

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f8f2d284f85"
down_revision: Union[str, Sequence[str], None] = "add_thumbnail_urls_list"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "thread" in tables:
        with op.batch_alter_table("thread", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "collection_count",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                    comment="被收藏次数",
                )
            )

    if "booklist" not in tables:
        op.create_table(
            "booklist",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.BigInteger(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("cover_image_url", sa.String(), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False),
            sa.Column("display_type", sa.Integer(), nullable=False),
            sa.Column("item_count", sa.Integer(), nullable=False),
            sa.Column("view_count", sa.Integer(), nullable=False),
            sa.Column("collection_count", sa.Integer(), nullable=False),
            sa.Column("display_thread_id", sa.BigInteger(), nullable=True),
            sa.Column("display_channel_id", sa.BigInteger(), nullable=True),
            sa.Column("display_guild_id", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_booklist_is_public"), "booklist", ["is_public"], unique=False
        )
        op.create_index(
            op.f("ix_booklist_owner_id"), "booklist", ["owner_id"], unique=False
        )
        op.create_index(op.f("ix_booklist_title"), "booklist", ["title"], unique=False)

    if "booklist_item" not in tables:
        op.create_table(
            "booklist_item",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("booklist_id", sa.Integer(), nullable=False),
            sa.Column("thread_id", sa.BigInteger(), nullable=False),
            sa.Column("display_order", sa.Integer(), nullable=False),
            sa.Column("comment", sa.String(), nullable=True),
            sa.Column("display_message_id", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("booklist_id", "thread_id", name="uq_booklist_thread"),
        )
        op.create_index(
            op.f("ix_booklist_item_booklist_id"),
            "booklist_item",
            ["booklist_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_booklist_item_display_order"),
            "booklist_item",
            ["display_order"],
            unique=False,
        )
        op.create_index(
            op.f("ix_booklist_item_thread_id"),
            "booklist_item",
            ["thread_id"],
            unique=False,
        )

    if "user_collection" not in tables:
        op.create_table(
            "user_collection",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=True),
            sa.Column("target_type", sa.Integer(), nullable=False),
            sa.Column("target_id", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("note", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id", "target_type", "target_id", name="uk_user_collection_target"
            ),
        )
        op.create_index(
            op.f("ix_user_collection_target_id"),
            "user_collection",
            ["target_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_user_collection_target_type"),
            "user_collection",
            ["target_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_user_collection_user_id"),
            "user_collection",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "thread" in tables:
        with op.batch_alter_table("thread", schema=None) as batch_op:
            batch_op.drop_column("collection_count")

    if "user_collection" in tables:
        op.drop_index(op.f("ix_user_collection_user_id"), table_name="user_collection")
        op.drop_index(
            op.f("ix_user_collection_target_type"), table_name="user_collection"
        )
        op.drop_index(
            op.f("ix_user_collection_target_id"), table_name="user_collection"
        )
        op.drop_table("user_collection")

    if "booklist_item" in tables:
        op.drop_index(op.f("ix_booklist_item_thread_id"), table_name="booklist_item")
        op.drop_index(
            op.f("ix_booklist_item_display_order"), table_name="booklist_item"
        )
        op.drop_index(op.f("ix_booklist_item_booklist_id"), table_name="booklist_item")
        op.drop_table("booklist_item")

    if "booklist" in tables:
        op.drop_index(op.f("ix_booklist_title"), table_name="booklist")
        op.drop_index(op.f("ix_booklist_owner_id"), table_name="booklist")
        op.drop_index(op.f("ix_booklist_is_public"), table_name="booklist")
        op.drop_table("booklist")
