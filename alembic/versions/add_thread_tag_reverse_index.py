"""add reverse lookup index for thread tags

Revision ID: add_thread_tag_reverse_index
Revises: unique_booklist_publish_booklist
"""

from typing import Sequence, Union

from alembic import op

revision: str = "add_thread_tag_reverse_index"
down_revision: Union[str, None] = "unique_booklist_publish_booklist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """并发创建 tag_id 前导索引，避免阻塞线上读写。"""
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_thread_tag_link_tag_id_thread_id",
            "thread_tag_link",
            ["tag_id", "thread_id"],
            unique=False,
            postgresql_concurrently=True,
            if_not_exists=True,
        )


def downgrade() -> None:
    """并发删除 tag_id 前导索引。"""
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_thread_tag_link_tag_id_thread_id",
            table_name="thread_tag_link",
            postgresql_concurrently=True,
            if_exists=True,
        )
