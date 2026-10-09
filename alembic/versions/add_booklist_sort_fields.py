"""新增 default_sort_method / default_sort_order（保留 display_type）

Revision ID: add_booklist_sort_fields
Revises: add_channel_table
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_booklist_sort_fields"
down_revision: Union[str, None] = "add_channel_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加新列（先 nullable）
    op.add_column(
        "booklist",
        sa.Column("default_sort_method", sa.String(), nullable=True),
    )
    op.add_column(
        "booklist",
        sa.Column("default_sort_order", sa.String(), nullable=True),
    )

    # 根据原有 display_type 批量设置新值
    op.execute(
        "UPDATE booklist SET"
        "  default_sort_method = CASE WHEN display_type = 2 THEN 'display_order' ELSE 'join_time' END,"
        "  default_sort_order   = CASE WHEN display_type = 2 THEN 'asc'           ELSE 'desc'      END"
    )

    # 改为 NOT NULL 并设置 server_default
    op.alter_column(
        "booklist", "default_sort_method", nullable=False, server_default="join_time"
    )
    op.alter_column(
        "booklist", "default_sort_order", nullable=False, server_default="desc"
    )

    # 创建索引
    op.create_index(
        "ix_booklist_default_sort_method",
        "booklist",
        ["default_sort_method"],
    )

    # display_type 暂时保留不删，兼容旧版本代码。下次数据库变更时再删


def downgrade() -> None:
    # 反向数据转换：根据新字段恢复 display_type
    op.execute(
        "UPDATE booklist SET"
        "  display_type = CASE WHEN default_sort_method = 'display_order' THEN 2 ELSE 1 END"
    )

    # 删除新列
    op.drop_index("ix_booklist_default_sort_method")
    op.drop_column("booklist", "default_sort_order")
    op.drop_column("booklist", "default_sort_method")
