from sqlalchemy import select


class TagDataRepository:
    """对指定单表提供标签业务使用的查询与持久化操作。"""

    def __init__(self, session, model):
        self.session = session
        self.model = model

    async def rows(self, *conditions, lock=False, limit=None):
        """按条件读取当前表，可在事务中锁定结果。"""
        statement = select(self.model).where(*conditions)
        if lock:
            statement = statement.with_for_update()
        if limit is not None:
            statement = statement.limit(limit)
        return list((await self.session.execute(statement)).scalars().all())

    async def one(self, *conditions, lock=False):
        """读取首个匹配记录。"""
        rows = await self.rows(*conditions, lock=lock, limit=1)
        return rows[0] if rows else None

    async def add(self, **values):
        """添加一条记录但不提交业务事务。"""
        row = self.model(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def remove(self, row):
        """移除可替换的辅助记录。"""
        await self.session.delete(row)
