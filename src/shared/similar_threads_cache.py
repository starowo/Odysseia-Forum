from shared.enum import CacheKeys


def get_similar_candidates_cache_key(thread_id: int, include_abyss: bool) -> str:
    """构建相似帖子候选池 Key。"""
    key_template = (
        CacheKeys.SIMILAR_CANDIDATES_ABYSS
        if include_abyss
        else CacheKeys.SIMILAR_CANDIDATES_STANDARD
    )
    return key_template.format(thread_id=thread_id)


async def invalidate_similar_candidate_pools(redis_client, thread_id: int) -> None:
    """删除一个源帖的普通区与深渊区候选池。"""
    await redis_client.delete(
        get_similar_candidates_cache_key(thread_id, include_abyss=False),
        get_similar_candidates_cache_key(thread_id, include_abyss=True),
    )
