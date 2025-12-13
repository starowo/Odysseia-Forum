from enum import Enum


class ApplicationStatus(str, Enum):
    """Banner申请状态"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
