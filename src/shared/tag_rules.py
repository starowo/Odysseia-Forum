from shared.tag_error import TagError


def validate_selection(current, desired, native_count, tags, relations):
    """验证新增标签集合，同时允许历史超限或冲突的纯删除操作。"""
    added = desired - current
    if not added:
        return
    invalid = sorted(
        i for i in added if i not in tags or not tags[i].enabled or tags[i].deleted_at
    )
    if invalid:
        raise TagError(
            "unavailable_tags",
            "标签不存在、已停用或已删除",
            tag_ids=[str(i) for i in invalid],
        )
    if len(desired) + native_count > 12:
        raise TagError("tag_limit", "原生和自定义标签合计不能超过 12 个")
    conflicts = [(a, b) for a, b in relations if a in desired and b in desired]
    if conflicts:
        raise TagError(
            "tag_conflict",
            "目标标签存在互斥关系",
            pairs=[[str(a), str(b)] for a, b in conflicts],
        )


def validate_graph(edges):
    """拒绝包含关系中的自环和有向循环。"""
    graph = {}
    for a, b in edges:
        graph.setdefault(a, set()).add(b)
    visiting, done = set(), set()
    for root in graph:
        stack = [(root, False)]
        while stack:
            node, exiting = stack.pop()
            if exiting:
                visiting.discard(node)
                done.add(node)
            elif node in visiting:
                raise TagError("relation_cycle", "包含关系不能形成循环")
            elif node not in done:
                visiting.add(node)
                stack.append((node, True))
                stack.extend((child, False) for child in graph.get(node, ()))
