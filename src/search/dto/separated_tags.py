from typing import List
from pydantic import BaseModel


class SeparatedTagsDTO(BaseModel):
    """分离的虚拟标签和所有可用标签的数据传输对象"""

    virtual_tags: List[str] = []
    """虚拟标签列表，已排序"""

    all_tags: List[str] = []
    """所有可用标签列表，虚拟标签固定排在最前"""

    @property
    def real_tags(self) -> List[str]:
        """真实标签列表（排除虚拟标签）"""
        virtual_set = set(self.virtual_tags)
        return [tag for tag in self.all_tags if tag not in virtual_set]
