from sqlalchemy import Integer, Text, column, func, literal_column, select, values
from sqlalchemy.ext.asyncio import AsyncSession

from shared.fts_utils import build_fts_conditions
from shared.text_utils import build_search_vector_text


class BannerTitleFilterRepository:
    """批量匹配频道 Banner 标题的反选关键词。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_excluded_ids(
        self,
        titles: dict[int, str],
        exclude_keywords: str,
        exemption_markers: list[str],
        redis_client=None,
    ) -> set[int]:
        """返回命中反选且未获豁免的轮播记录 ID。"""
        if not titles or not exclude_keywords.strip():
            return set()

        # 标题分词后使用绑定参数构建临时行集，不拼接用户文本为 SQL。
        rows = (
            values(column("banner_id", Integer), column("tokens", Text))
            .data(
                [
                    (banner_id, build_search_vector_text(title, None) or "")
                    for banner_id, title in titles.items()
                ]
            )
            .alias("banner_titles")
        )
        vector = func.to_tsvector(literal_column("'simple'"), rows.c.tokens)
        filters = await build_fts_conditions(
            vector,
            keywords=None,
            exclude_keywords=exclude_keywords,
            exemption_markers=exemption_markers,
            redis_client=redis_client,
        )
        if not filters.has_exclude:
            return set()
        result = await self.session.execute(
            select(rows.c.banner_id).where(filters.exclude_condition)
        )
        return set(result.scalars().all())
