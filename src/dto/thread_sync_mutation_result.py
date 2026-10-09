from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThreadSyncMutationResult:
    """描述帖子同步写库后的变化。"""

    created: bool
    tags_changed: bool
