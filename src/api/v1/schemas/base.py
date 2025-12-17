from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

DataType = TypeVar("DataType")


class PaginatedResponse(BaseModel, Generic[DataType]):
    """
    标准分页响应模型
    """

    total: int = Field(description="符合条件的总项目数")
    limit: int = Field(description="本次查询每页的项目数")
    offset: int = Field(description="本次查询的偏移量")
    results: List[DataType]
