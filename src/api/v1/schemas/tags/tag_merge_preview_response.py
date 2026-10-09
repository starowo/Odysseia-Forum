from pydantic import BaseModel, Field


class TagMergePreviewResponse(BaseModel):
    """合并预检结果；执行时重新检查权限、版本和冲突。"""

    source_tag_id: str = Field(description="即将软删除的标签 ID")
    """旧标签 ID"""
    target_tag_id: str = Field(description="合并后保留的标签 ID")
    """保留标签 ID"""
    source_name: str = Field(description="旧标签标准名")
    """旧标准名"""
    target_name: str = Field(description="保留标签标准名，必须与旧标签完全相同")
    """保留标准名"""
    source_is_abyss: bool = Field(description="待合并旧标签是否为深渊向")
    """旧标签的深渊向标识"""
    target_is_abyss: bool = Field(description="保留标签是否为深渊向")
    """目标标签的深渊向标识，合并结果沿用该值"""
    version: str = Field(description="预检版本，执行时原样传回")
    """预检版本"""
    can_merge: bool = Field(description="当前是否满足合并条件")
    """是否可合并"""
    conflicts: list[str] = Field(description="阻止合并的中文原因，无冲突时为空")
    """合并冲突"""
    binding_count: int = Field(description="旧标签受影响的有效绑定数量")
    """有效绑定数量"""
    proposal_count: int = Field(description="旧标签即将结束的待审核申请数量")
    """待审核申请数量"""
    relation_count: int = Field(description="旧标签涉及的关系数量")
    """标签关系数量"""
