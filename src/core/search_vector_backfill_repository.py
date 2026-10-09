"""直接从 PostgreSQL 原文回填搜索向量的批量仓储。"""

import json

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncConnection

from dto.search.search_vector_source_dto import SearchVectorSourceDTO

# SQL 标识符只取自固定映射，不接受命令行文本拼接。
_SOURCE_COLUMNS = {"thread": "first_message_excerpt", "booklist": "description"}


class SearchVectorBackfillRepository:
    """批量读取原文，并以原文快照为条件更新单表搜索向量。"""

    def __init__(self, connection: AsyncConnection, table: str):
        """绑定当前批次事务和经过白名单校验的表。"""
        self.body_column = _SOURCE_COLUMNS[table]
        self.table = table
        self.connection = connection

    async def get_scan_limit(self) -> int:
        """记录启动时的主键扫描上限。"""
        result = await self.connection.execute(
            text(f"SELECT COALESCE(MAX(id), 0) FROM {self.table}")
        )
        return result.scalar_one()

    async def get_batch(
        self, cursor: int, upper_bound: int, batch_size: int
    ) -> list[SearchVectorSourceDTO]:
        """按主键分页读取固定扫描范围内的原文。"""
        result = await self.connection.execute(
            text(
                f"SELECT id, title, {self.body_column} AS body FROM {self.table} "
                "WHERE id > :cursor AND id <= :upper_bound ORDER BY id LIMIT :batch_size"
            ),
            {"cursor": cursor, "upper_bound": upper_bound, "batch_size": batch_size},
        )
        return [SearchVectorSourceDTO(**row) for row in result.mappings()]

    async def read_sources(self, ids: list[int]) -> list[SearchVectorSourceDTO]:
        """批量重新读取并发变化的原文，缺失主键表示记录已删除。"""
        result = await self.connection.execute(
            text(
                f"SELECT id, title, {self.body_column} AS body FROM {self.table} "
                "WHERE id IN :ids ORDER BY id"
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )
        return [SearchVectorSourceDTO(**row) for row in result.mappings()]

    async def update_batch(self, sources: list[SearchVectorSourceDTO]) -> set[int]:
        """仅原文仍一致时批量写向量，绕过 ORM 以保留书单更新时间。"""
        # PostgreSQL 在锁等待后重检原文条件，避免把旧快照的向量写回新原文。
        result = await self.connection.execute(
            text(
                f"UPDATE {self.table} AS target SET search_vector = "
                "CASE WHEN batch.tokens IS NULL THEN NULL "
                "ELSE to_tsvector('simple', batch.tokens) END "
                "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) "
                "AS batch(id integer, title text, body text, tokens text) "
                "WHERE target.id = batch.id "
                "AND target.title IS NOT DISTINCT FROM batch.title "
                f"AND target.{self.body_column} IS NOT DISTINCT FROM batch.body "
                "RETURNING target.id"
            ),
            {"rows": json.dumps([source.model_dump() for source in sources])},
        )
        return set(result.scalars())
