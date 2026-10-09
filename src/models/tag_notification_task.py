from datetime import datetime

from sqlalchemy import BigInteger, Column

from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class TagNotificationTask(SQLModel, table=True):
    """保存审核通知的持久化发送任务及重试状态。"""

    __tablename__ = "tag_notification_task"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        description="通知发送任务的内部主键",
    )
    """通知发送任务的内部主键"""

    proposal_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True, unique=True),
        description="关联标签申请的内部 ID；每个申请最多创建一条通知任务",
    )
    """关联标签申请的内部 ID；每个申请最多创建一条通知任务"""

    kind: str = Field(
        default="proposal",
        description="通知类型：proposal 审核，converted 转换待分类，conflict 分类冲突，collision 同名概念待处理",
    )
    """持久化发送任务的业务类型"""

    tag_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger),
        description="生命周期通知关联的内部标签 ID",
    )
    """分类消息关联的标签实体"""

    status: str = Field(
        default="pending",
        index=True,
        description="任务状态：pending 为待发送或待重试，sent 为已发送或站内兜底完成，cancelled 为申请已结束而取消",
    )
    """任务状态：pending 为待发送或待重试，sent 为已发送或站内兜底完成，cancelled 为申请已结束而取消"""

    attempts: int = Field(
        default=0, description="已执行的通知发送尝试次数，用于计算失败重试间隔"
    )
    """已执行的通知发送尝试次数，用于计算失败重试间隔"""

    error: str | None = Field(
        default=None,
        description="最近一次发送异常类型或站内通知兜底原因；无异常记录时为空",
    )
    """最近一次发送异常类型或站内通知兜底原因；无异常记录时为空"""

    available_at: datetime = Field(
        default_factory=utc_now,
        index=True,
        description="允许下一次领取发送任务的时间（UTC）；失败后按退避规则延后",
    )
    """允许下一次领取发送任务的时间（UTC）；失败后按退避规则延后"""
