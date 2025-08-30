from .tag import Tag
from .thread import Thread
from .thread_tag_link import ThreadTagLink
from .tag_vote import TagVote
from .user_search_preferences import UserSearchPreferences
from .mutex_tag_group import MutexTagGroup
from .mutex_tag_rule import MutexTagRule

# 这一行是为了让 Alembic/SQLModel 能够发现所有模型
__all__ = [
    "Tag",
    "Thread",
    "ThreadTagLink",
    "TagVote",
    "UserSearchPreferences",
    "MutexTagGroup",
    "MutexTagRule",
]
