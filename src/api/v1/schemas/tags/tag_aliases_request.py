from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class TagAliasesRequest(BaseModel):
    """完整替换别名集合，空列表表示清空。"""

    model_config = ConfigDict(extra="forbid")

    aliases: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
        ]
    ] = Field(
        max_length=100, description="替换后的完整检索别名列表；空列表表示清空所有别名"
    )
    """替换后的完整检索别名列表；空列表表示清空"""
