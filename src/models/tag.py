from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Index, Text, false, text
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models import Thread


class Tag(SQLModel, table=True):
    """统一保存原生与自定义标签实体及生命周期状态。"""

    # 自定义标准名的唯一性包含软删除记录，避免重建实体绕过治理历史。
    __table_args__ = (
        Index(
            "uq_custom_tag_category_name",
            "category",
            "name",
            unique=True,
            postgresql_where=text("source = 'custom'"),
        ),
        Index(
            "uq_live_discord_tag_name",
            "name",
            unique=True,
            postgresql_where=text("source = 'discord' AND deleted_at IS NULL"),
        ),
        CheckConstraint(
            "source IN ('custom', 'discord') AND (category BETWEEN 1 AND 7 OR category IS NULL) AND (source <> 'custom' OR category IS NOT NULL OR originated_from_discord)",
            name="ck_tag_source_category",
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        description="本项目内部标签主键，由正数 BIGINT 序列生成；与 Discord 标签 ID 分离",
    )
    """本项目内部标签主键，由正数 BIGINT 序列生成；与 Discord 标签 ID 分离"""

    name: str = Field(
        index=True, description="标签名称；自定义标签保存不含分类前缀的标准名"
    )
    """标签名称；自定义标签保存不含分类前缀的标准名"""

    description: str = Field(
        default="",
        sa_column=Column(Text, nullable=False, server_default=""),
        description="标签含义的纯文本说明，最多 2000 字；空字符串表示未填写",
    )
    """标签含义的纯文本说明；未填写时为空字符串，DC 同步不覆盖人工描述"""

    is_abyss: bool = Field(
        default=False,
        sa_column=Column(
            Boolean,
            nullable=False,
            server_default=false(),
        ),
        description="是否为深渊向 TAG；仅控制候选发现可见性，不改变既有绑定展示",
    )
    """深渊向标识；已有绑定仍随内容正常展示"""

    source: str = Field(
        default="discord",
        index=True,
        description="标签来源：discord 为有有效 DC 来源的标准概念，custom 为自定义标签",
    )
    """标签来源：discord 为有有效 DC 来源的标准概念，custom 为自定义标签"""

    originated_from_discord: bool = Field(
        default=False,
        description="是否具有 DC 来源历史；允许转换后的自定义概念暂未分类",
    )
    """保留概念来源背景，不用于判断帖子绑定的操作权限"""

    category: int | None = Field(
        default=None,
        description="自定义分类：1=癖好，2=作品，3=角色，4=特质，5=情节，6=背景，7=玩法；DC 概念和未分类转换标签可为空",
    )
    """自定义分类：1=癖好，2=作品，3=角色，4=特质，5=情节，6=背景，7=玩法；DC 概念和未分类转换标签可为空"""

    enabled: bool = Field(
        default=True,
        description="是否允许新增绑定和提议；停用后已有绑定仍保留展示、搜索与投票",
    )
    """是否允许新增绑定和提议；停用后已有绑定仍保留展示、搜索与投票"""

    deleted_at: datetime | None = Field(
        default=None,
        description="软删除时间（UTC）；为空表示未删除，恢复实体时不恢复旧绑定",
    )
    """软删除时间（UTC）；为空表示未删除，恢复实体时不恢复旧绑定"""

    threads: list["Thread"] = Relationship(
        sa_relationship_kwargs={
            "secondary": "tag_binding",
            "primaryjoin": "and_(Tag.id == foreign(TagBinding.tag_id), Tag.deleted_at.is_(None))",
            "secondaryjoin": "and_(Thread.id == foreign(TagBinding.target_id), TagBinding.target_type == 'thread', TagBinding.ended_at.is_(None))",
            "viewonly": True,
        },
    )
    """通过统一有效绑定查询帖子；迁移备份表不参与 ORM 关系"""
