from sqlalchemy import BigInteger, CheckConstraint, Column
from sqlmodel import Field, SQLModel


class TagVote(SQLModel, table=True):
    """保存用户对某轮自定义挂标的当前投票。"""

    __tablename__ = "tag_vote"

    binding_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True),
        description="挂标轮次 ID，与用户 ID 组成联合主键；不是标签实体 ID",
    )
    """挂标轮次 ID，与用户 ID 组成联合主键；不是标签实体 ID"""

    user_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True),
        description="投票用户的 Discord ID；同一轮次每人最多一票",
    )
    """投票用户的 Discord ID；同一轮次每人最多一票"""

    vote: int = Field(
        description="当前票值：1 为赞，-1 为踩；撤票时删除此记录，变更历史保留在操作日志"
    )
    """当前票值：1 为赞，-1 为踩；撤票时删除此记录，变更历史保留在操作日志"""

    __table_args__ = (CheckConstraint("vote IN (-1, 1)", name="ck_tag_vote"),)
