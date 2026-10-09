"""change booklist publish uniqueness to booklist

Revision ID: unique_booklist_publish_booklist
Revises: add_booklist_publish_table
Create Date: 2026-07-03 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "unique_booklist_publish_booklist"
down_revision: Union[str, None] = "add_booklist_publish_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_booklist_publish_thread", "booklist_publish", type_="unique")
    op.create_unique_constraint(
        "uq_booklist_publish_booklist", "booklist_publish", ["booklist_id"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_booklist_publish_booklist", "booklist_publish", type_="unique"
    )
    op.create_unique_constraint(
        "uq_booklist_publish_thread",
        "booklist_publish",
        ["booklist_id", "thread_id"],
    )
