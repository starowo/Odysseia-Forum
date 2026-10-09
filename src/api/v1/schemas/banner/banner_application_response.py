"""Banner申请响应Schema"""

from typing import Optional

from pydantic import BaseModel


class BannerApplicationResponse(BaseModel):
    """Banner申请响应模型"""

    success: bool
    message: str
    application_id: Optional[int] = None
