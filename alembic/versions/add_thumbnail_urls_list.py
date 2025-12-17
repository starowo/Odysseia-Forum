"""add thumbnail urls column

Revision ID: add_thumbnail_urls_list
Revises: add_thread_follow_update
Create Date: 2025-11-24 03:40:00.000000

"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import and_


# revision identifiers, used by Alembic.
revision = "add_thumbnail_urls_list"
down_revision = "add_banner_system"
branch_labels = None
depends_on = None


def _thread_table():
    return sa.table(
        "thread",
        sa.column("id", sa.Integer),
        sa.column("thumbnail_url", sa.String),
        sa.column("thumbnail_urls", sa.JSON),
    )


def _normalize_thumbnail_list(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def upgrade() -> None:
    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "thumbnail_urls",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )

    connection = op.get_bind()
    thread_table = _thread_table()

    rows = connection.execute(
        sa.select(thread_table.c.id, thread_table.c.thumbnail_url).where(
            and_(
                thread_table.c.thumbnail_url.isnot(None),
                thread_table.c.thumbnail_url != "",
            )
        )
    ).all()

    for row in rows:
        connection.execute(
            thread_table.update()
            .where(thread_table.c.id == row.id)
            .values(thumbnail_urls=[row.thumbnail_url])
        )

    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.drop_column("thumbnail_url")
        batch_op.alter_column("thumbnail_urls", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.add_column(sa.Column("thumbnail_url", sa.String(), nullable=True))

    connection = op.get_bind()
    thread_table = _thread_table()

    rows = connection.execute(
        sa.select(thread_table.c.id, thread_table.c.thumbnail_urls)
    ).all()

    for row in rows:
        urls = _normalize_thumbnail_list(row.thumbnail_urls)
        if not urls:
            continue
        connection.execute(
            thread_table.update()
            .where(thread_table.c.id == row.id)
            .values(thumbnail_url=urls[0])
        )

    with op.batch_alter_table("thread", schema=None) as batch_op:
        batch_op.drop_column("thumbnail_urls")
