"""移除已废弃的 display_type 列

Revision ID: drop_display_type
Revises: add_booklist_sort_fields
Create Date: 2026-06-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "drop_display_type"
down_revision: Union[str, None] = "add_booklist_sort_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("booklist", "display_type")


def downgrade() -> None:
    op.add_column(
        "booklist",
        sa.Column(
            "display_type", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
    )
    # 根据新字段恢复 display_type
    op.execute(
        "UPDATE booklist SET"
        "  display_type = CASE WHEN default_sort_method = 'display_order' THEN 2 ELSE 1 END"
    )
