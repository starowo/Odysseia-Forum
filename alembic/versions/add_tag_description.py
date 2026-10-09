"""为标准标签添加人工维护的描述；降级会丢失所有标签描述。"""

import sqlalchemy as sa

from alembic import op

revision = "add_tag_description"
down_revision = "normalize_discord_tags"
branch_labels = None
depends_on = None


def upgrade():
    """新增描述列，为已有记录及未指定描述的新记录提供空字符串默认值。"""
    op.add_column(
        "tag",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )


def downgrade():
    """删除描述列；其内容不可由本迁移恢复。"""
    op.drop_column("tag", "description")
