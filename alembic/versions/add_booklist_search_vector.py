"""add booklist search_vector TSVECTOR column with GIN index

使用 rjieba 分词分批回填所有现有行，确保与应用层分词一致。

Revision ID: add_booklist_search_vector
Revises: drop_display_type
Create Date: 2026-06-26
"""

import logging
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_booklist_search_vector"
down_revision: Union[str, None] = "drop_display_type"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

logger = logging.getLogger("alembic")

BATCH_SIZE = 500  # 每批更新的行数


def upgrade() -> None:
    # ── 0. 预检查：确认 rjieba 可用 ──
    logger.info("预检查 rjieba 可用性...")
    try:
        from shared.text_utils import build_search_vector_text

        # 烟雾测试
        test_result = build_search_vector_text("测试书单", "这是一个测试")
        assert test_result and len(test_result) > 0, "rjieba 分词返回空结果"
        logger.info(f"rjieba 预检查通过（测试分词结果: {test_result[:50]}...）")
    except Exception as e:
        logger.error(f"rjieba 预检查失败: {e}")
        raise RuntimeError(f"rjieba 不可用，无法回填 search_vector: {e}") from e

    # ── 1. 添加可空 TSVECTOR 列 ──
    logger.info("添加 search_vector TSVECTOR 列...")
    op.add_column(
        "booklist",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR,
            nullable=True,
        ),
    )

    # ── 2. 用 rjieba 分词分批回填 ──
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id, title, description FROM booklist")).fetchall()

    total = len(rows)
    logger.info(f"booklist 表共 {total} 行，开始用 rjieba 分批回填 search_vector...")

    # 先对所有行做 rjieba 分词
    update_pairs: list[tuple[int, str]] = []
    for row_id, title, description in rows:
        tokens_text = build_search_vector_text(title, description)
        if tokens_text:
            update_pairs.append((row_id, tokens_text))
    logger.info(f"分词完成，{len(update_pairs)}/{total} 行有可索引文本")

    # 分批 UPDATE，使用 UPDATE ... FROM (VALUES ...) 批量更新
    for batch_start in range(0, len(update_pairs), BATCH_SIZE):
        batch = update_pairs[batch_start : batch_start + BATCH_SIZE]

        values_parts: list[str] = []
        params: dict = {}
        for j, (row_id_val, tokens) in enumerate(batch):
            id_key = f"id_{j}"
            tok_key = f"tok_{j}"
            values_parts.append(f"(:{id_key}, :{tok_key})")
            params[id_key] = row_id_val
            params[tok_key] = tokens

        values_clause = ", ".join(values_parts)
        conn.execute(
            text(
                f"UPDATE booklist SET search_vector = to_tsvector('simple', v.tokens) "
                f"FROM (VALUES {values_clause}) AS v(id, tokens) "
                f"WHERE booklist.id = v.id::integer"
            ),
            params,
        )

        done = min(batch_start + BATCH_SIZE, len(update_pairs))
        logger.info(f"  已回填 {done}/{len(update_pairs)} 行")

    # ── 2b. 验证回填结果 ──
    null_count = conn.execute(
        text("SELECT COUNT(*) FROM booklist WHERE search_vector IS NULL")
    ).scalar()
    populated = total - (null_count or 0)
    logger.info(
        f"回填验证: {populated}/{total} 行 search_vector 非空, {null_count} 行为 NULL"
    )

    # ── 3. 创建 GIN 索引 ──
    logger.info("创建 GIN 索引 ix_booklist_search_vector...")
    op.create_index(
        "ix_booklist_search_vector",
        "booklist",
        ["search_vector"],
        postgresql_using="gin",
    )
    logger.info("迁移 add_booklist_search_vector 完成")


def downgrade() -> None:
    logger.info("回滚: 删除 GIN 索引 + search_vector 列...")
    op.drop_index("ix_booklist_search_vector")
    op.drop_column("booklist", "search_vector")
    logger.info("回滚完成")
