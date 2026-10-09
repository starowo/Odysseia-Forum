"""为统一标签增加深渊向标识。"""

import sqlalchemy as sa

from alembic import op

revision = "add_abyss_tag_flag"
down_revision = "add_tag_description"
branch_labels = None
depends_on = None


def upgrade():
    """新增非空深渊向标识，既有标签默认按正常向处理。"""
    op.add_column(
        "tag",
        sa.Column(
            "is_abyss",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    """删除深渊向标识。"""
    op.drop_column("tag", "is_abyss")
