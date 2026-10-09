from pydantic import BaseModel, Field


class ThreadSyncResult(BaseModel):
    """帖子同步的可观察结果。"""

    success: bool = Field(description="帖子数据库事务是否已成功提交")
    error_code: str | None = Field(
        default=None,
        description="可安全写入 Redis 与日志的稳定失败码，不含异常详情或 URL",
    )
