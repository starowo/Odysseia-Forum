from typing import List, Union, Any

from pydantic import BaseModel, field_validator


class BooklistItemsDeleteRequest(BaseModel):
    thread_ids: List[Union[int, str]]

    @field_validator("thread_ids", mode="before")
    @classmethod
    def convert_ids_to_int(cls, v: Any) -> Any:
        """
        在 Pydantic 校验前，将字符串形式的 Discord ID 转换为 int。
        """
        if v is None:
            return v

        if isinstance(v, list):
            processed = []
            for item in v:
                if isinstance(item, str) and item.isdigit():
                    processed.append(int(item))
                else:
                    processed.append(item)
            return processed

        return v
