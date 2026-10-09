"""为 thread / booklist 设置 fillfactor

Revision ID: set_table_storage_params
Revises: add_booklist_search_vector
Create Date: 2026-06-26
"""

from typing import Union

from alembic import op

revision: str = "set_table_storage_params"
down_revision: Union[str, None] = "add_booklist_search_vector"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE thread SET (fillfactor = 90)")
    op.execute("ALTER TABLE booklist SET (fillfactor = 90)")


def downgrade() -> None:
    op.execute("ALTER TABLE thread RESET (fillfactor)")
    op.execute("ALTER TABLE booklist RESET (fillfactor)")
