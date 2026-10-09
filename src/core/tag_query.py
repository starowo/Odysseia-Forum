from collections.abc import Sequence
from typing import Any

from sqlalchemy import String, and_, column, func, or_, select, union_all, values
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col

from dto.custom_tag_binding_response import CustomTagBindingResponse
from models import Tag, TagAlias
from models.tag_binding import TagBinding
from shared.enum.tag_category import TagCategory


async def require_current_tag_ids(session, ids):
    """显式使用缺失或软删除 ID 时提示刷新，不展开或重定向旧标签。"""
    ids = {int(i) for i in ids}
    if not ids:
        return
    valid = set(
        (
            await session.execute(
                select(col(Tag.id)).where(
                    col(Tag.id).in_(ids), col(Tag.deleted_at).is_(None)
                )
            )
        ).scalars()
    )
    if ids - valid:
        from shared.tag_error import TagError

        raise TagError("tags_changed", "标签已发生变化，请刷新后重试")


def tag_filters(
    kind: str,
    target_column: Any,
    included: Sequence[int | str] | None,
    excluded: Sequence[int | str] | None,
    logic: str = "and",
    included_groups: Sequence[Sequence[int]] = (),
) -> list[ColumnElement[bool]]:
    """按统一内部 ID 筛选目标实际绑定的原生和自定义标签。"""

    def matches(ids: Sequence[int]) -> ColumnElement[bool]:
        """合并同一批 ID 在两类绑定中的命中结果。"""
        custom = (
            select(col(TagBinding.id))
            .join(Tag, col(Tag.id) == col(TagBinding.tag_id))
            .where(
                col(TagBinding.target_type) == kind,
                col(TagBinding.target_id) == target_column,
                col(TagBinding.ended_at).is_(None),
                col(Tag.deleted_at).is_(None),
                col(Tag.id).in_(ids),
            )
            .exists()
        )
        return custom

    conditions: list[ColumnElement[bool]] = []
    if included:
        clauses = [matches([int(tag_id)]) for tag_id in set(included)]
        conditions.append(or_(*clauses) if logic == "or" else and_(*clauses))
    if included_groups:
        clauses = [matches(group) for group in included_groups]
        conditions.append(or_(*clauses) if logic == "or" else and_(*clauses))
    if excluded:
        conditions.append(~matches([int(v) for v in excluded]))
    return conditions


async def tag_name_filters(
    session: AsyncSession,
    kind: str,
    target_column: Any,
    included: Sequence[str] | None,
    excluded: Sequence[str] | None,
    logic: str = "and",
) -> list[ColumnElement[bool]]:
    """一次解析标准名和不区分大小写的完整别名，按名称组筛选有效绑定。"""
    names = list(dict.fromkeys([*(included or []), *(excluded or [])]))
    if not names:
        return []
    # 保留输入名称与实体的对应关系，不能将多个 AND 名称组展平。
    requested = values(column("name", String), name="requested_names").data(
        [(name,) for name in names]
    )
    canonical = (
        select(requested.c.name, col(Tag.id))
        .select_from(requested.join(Tag, col(Tag.name) == requested.c.name))
        .where(col(Tag.deleted_at).is_(None))
    )
    aliases = (
        select(requested.c.name, col(Tag.id))
        .select_from(
            requested.join(
                TagAlias, func.lower(col(TagAlias.name)) == func.lower(requested.c.name)
            ).join(Tag, col(Tag.id) == col(TagAlias.tag_id))
        )
        .where(col(Tag.deleted_at).is_(None))
    )
    groups: dict[str, set[int]] = {name: set() for name in names}
    for name, tag_id in (await session.execute(union_all(canonical, aliases))).all():
        groups[name].add(tag_id)
    # 空包含组保留为不匹配；空排除组不产生额外限制。
    return tag_filters(
        kind,
        target_column,
        [],
        list({tag_id for name in (excluded or []) for tag_id in groups[name]}),
        logic,
        [list(groups[name]) for name in dict.fromkeys(included or [])],
    )


async def load_custom_tags(
    session: AsyncSession, kind: str, target_ids: Sequence[int]
) -> dict[int, list[CustomTagBindingResponse]]:
    """批量读取标签展示数据，避免逐目标查询和缓存陈旧票数。"""
    if not target_ids:
        return {}
    statement = (
        select(TagBinding, Tag)
        .join(Tag, col(Tag.id) == col(TagBinding.tag_id))
        .where(
            col(TagBinding.target_type) == kind,
            col(TagBinding.target_id).in_(target_ids),
            col(TagBinding.ended_at).is_(None),
            col(TagBinding.binding_source) == "local",
            col(Tag.deleted_at).is_(None),
        )
        .order_by(col(Tag.category), col(Tag.name))
    )
    result: dict[int, list[CustomTagBindingResponse]] = {}
    for binding, tag in (await session.execute(statement)).all():
        result.setdefault(binding.target_id, []).append(
            CustomTagBindingResponse(
                id=str(tag.id),
                name=tag.name,
                is_abyss=getattr(tag, "is_abyss", False),
                category=tag.category,
                category_name=TagCategory(tag.category).name if tag.category else None,
                source=tag.source,
                enabled=tag.enabled,
                binding_id=str(binding.id),
                upvotes=binding.upvotes,
                downvotes=binding.downvotes,
            )
        )
    return result
