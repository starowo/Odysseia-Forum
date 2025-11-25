# 搜索联想功能 - 技术方案

## 概述

为搜索框添加实时联想功能，当用户输入时显示匹配的帖子标题，提升搜索效率和用户体验。

## 功能描述

### 用户交互流程
1. 用户在搜索框输入关键词（至少 2 个字符）
2. 系统实时显示匹配的帖子标题
3. 显示相似度评分（可选）
4. 用户可以直接点击跳转到帖子

### 示例
```
用户输入: "React性能"

建议下拉框:
┌─────────────────────────────────────┐
│ 📝 历史搜索                          │
│   React性能优化                      │
├─────────────────────────────────────┤
│ 📄 匹配帖子                          │
│   ⚡ React性能优化最佳实践 (95%)     │
│   ⚡ React 18 性能提升详解 (88%)     │
│   ⚡ 提升React应用性能的10个技巧(82%)│
├─────────────────────────────────────┤
│ 🏷️ 标签建议                         │
│   React, 性能优化                    │
└─────────────────────────────────────┘
```

---

## 技术方案

### 方案 A: 轻量级实现（临时方案）

#### 前端实现
复用现有 `POST /search/` API，添加防抖优化：

```tsx
// SearchSuggestions.tsx 扩展
const { data: threadSuggestions } = useQuery({
  queryKey: ['search-suggest', debouncedQuery],
  queryFn: async () => {
    if (debouncedQuery.length < 2) return [];
    
    const res = await searchApi.search({
      query: debouncedQuery,
      limit: 5,
      sort_method: 'relevance',
    });
    
    return res.results.map(thread => ({
      id: thread.id,
      title: thread.title,
      channel_name: thread.channel_name,
    }));
  },
  enabled: debouncedQuery.length >= 2 && debouncedQuery.length < 50,
  staleTime: 60 * 1000,
});
```

#### 优点
- ✅ 无需后端改动
- ✅ 立即可用
- ✅ 实现简单

#### 缺点
- ❌ 响应较慢（200-500ms）
- ❌ 无相似度评分
- ❌ 请求代价高（完整搜索）

---

### 方案 B: 专用联想 API（推荐）

#### 后端 API 设计

##### 新增端点
```
GET /search/suggest
```

##### 请求参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | 是 | 搜索关键词 |
| `limit` | integer | 否 | 返回数量，默认 10 |
| `channel_id` | string | 否 | 限定频道 |

##### 响应格式
```json
{
  "suggestions": [
    {
      "id": "123456789",
      "title": "React性能优化最佳实践",
      "channel_id": "987654321",
      "channel_name": "技术分享",
      "match_score": 0.95,
      "highlight": "<mark>React</mark><mark>性能</mark>优化最佳实践"
    },
    {
      "id": "123456790",
      "title": "React 18 性能提升详解",
      "match_score": 0.88,
      "highlight": "<mark>React</mark> 18 <mark>性能</mark>提升详解"
    }
  ],
  "total": 127
}
```

##### 性能要求
- 响应时间: < 100ms (P95)
- 并发支持: 100 QPS
- 缓存策略: 热词缓存 5 分钟

---

#### 后端实现建议

##### 选项 1: PostgreSQL 全文搜索
使用 `pg_trgm` 扩展实现模糊匹配：

```sql
-- 创建索引
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX threads_title_trgm_idx ON threads USING gin (title gin_trgm_ops);

-- 查询示例
SELECT 
  id,
  title,
  channel_id,
  channel_name,
  similarity(title, $1) as match_score
FROM threads
WHERE title % $1  -- 三元组相似度操作符
ORDER BY similarity(title, $1) DESC
LIMIT $2;
```

**优点**：
- 简单，无需额外服务
- 支持中文（需配置）
- 性能较好

**缺点**：
- 精确度一般
- 中文分词需要额外配置

---

##### 选项 2: Elasticsearch（如果已有）
```json
{
  "query": {
    "multi_match": {
      "query": "React性能",
      "fields": ["title^3", "content"],
      "type": "phrase_prefix",
      "fuzziness": "AUTO"
    }
  },
  "highlight": {
    "fields": {
      "title": {}
    }
  },
  "size": 10
}
```

**优点**：
- 性能极佳
- 支持高亮
- 支持中文分词（IK Analyzer）

**缺点**：
- 需要额外服务
- 维护成本高

---

##### 选项 3: 内存缓存 + 前缀树（适合小规模）
```python
from typing import List, Tuple
import jieba

class ThreadSuggester:
    def __init__(self):
        self.trie = {}  # 前缀树
        self.threads = {}  # id -> thread 映射
        
    def build_index(self, threads: List[Thread]):
        """构建倒排索引"""
        for thread in threads:
            # 分词
            tokens = jieba.cut_for_search(thread.title)
            for token in tokens:
                if token not in self.trie:
                    self.trie[token] = []
                self.trie[token].append(thread.id)
            self.threads[thread.id] = thread
    
    def suggest(self, query: str, limit: int = 10) -> List[Tuple[Thread, float]]:
        """搜索建议"""
        tokens = jieba.cut_for_search(query)
        candidates = {}
        
        for token in tokens:
            if token in self.trie:
                for thread_id in self.trie[token]:
                    candidates[thread_id] = candidates.get(thread_id, 0) + 1
        
        # 按匹配度排序
        results = sorted(
            candidates.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [(self.threads[tid], score/len(tokens)) for tid, score in results]
```

**优点**：
- 极快（内存查询）
- 可控性强

**缺点**：
- 内存占用
- 需要定期重建索引

---

#### 前端实现

```tsx
// 在 SearchSuggestions.tsx 中添加
interface ThreadSuggestion {
  id: string;
  title: string;
  channel_name: string;
  match_score: number;
  highlight?: string;
}

const { data: threadSuggestions } = useQuery({
  queryKey: ['suggest-threads', debouncedQuery],
  queryFn: async () => {
    if (debouncedQuery.length < 2) return [];
    
    const res = await apiClient.get<{ suggestions: ThreadSuggestion[] }>(
      '/search/suggest',
      {
        params: {
          q: debouncedQuery,
          limit: 5,
          channel_id: selectedChannel || undefined,
        },
      }
    );
    
    return res.data.suggestions;
  },
  enabled: debouncedQuery.length >= 2,
  staleTime: 30 * 1000,
});

// 渲染
{threadSuggestions?.map((suggestion) => (
  <button
    key={suggestion.id}
    onClick={() => navigateToThread(suggestion.id)}
    className="flex items-start gap-3 px-4 py-2.5 hover:bg-[var(--od-bg-tertiary)]"
  >
    <MessageSquare className="h-4 w-4 mt-0.5 text-[var(--od-text-tertiary)]" />
    <div className="flex-1 text-left">
      <div 
        className="text-sm text-[var(--od-text-primary)]"
        dangerouslySetInnerHTML={{ __html: suggestion.highlight || suggestion.title }}
      />
      <div className="text-xs text-[var(--od-text-tertiary)]">
        {suggestion.channel_name} · {Math.round(suggestion.match_score * 100)}% 匹配
      </div>
    </div>
  </button>
))}
```

---

## 性能优化

### 防抖（Debounce）
```tsx
const [debouncedQuery] = useDebounce(currentQuery, 300);
```

### 请求取消
```tsx
const abortControllerRef = useRef<AbortController>();

useEffect(() => {
  // 取消之前的请求
  abortControllerRef.current?.abort();
  abortControllerRef.current = new AbortController();
  
  // ... 发起新请求
}, [currentQuery]);
```

### 缓存策略
- React Query 缓存: 30 秒
- 后端缓存: 热词 5 分钟
- CDN 缓存: 不缓存（动态内容）

---

## 实施计划

### Phase 1: 后端 API 开发
- [ ] 设计 API 接口
- [ ] 选择搜索方案（PostgreSQL / ES / 内存）
- [ ] 实现联想逻辑
- [ ] 性能测试（目标 < 100ms）
- [ ] 添加监控和日志

### Phase 2: 前端集成
- [ ] 扩展 `SearchSuggestions` 组件
- [ ] 添加防抖和请求取消
- [ ] 实现高亮显示
- [ ] 添加相似度展示
- [ ] 键盘导航支持

### Phase 3: 优化
- [ ] A/B 测试（是否提升搜索效率）
- [ ] 性能优化
- [ ] 用户反馈收集

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 响应时间过慢 | 高 | 添加缓存，优化查询，前端降级 |
| 服务器负载增加 | 中 | 限流，CDN，缓存 |
| 中文分词不准确 | 中 | 使用专业分词库（jieba, IK） |
| 用户不习惯 | 低 | 设置开关，逐步推广 |

---

## 成本估算

### 开发成本
- 后端开发: 2-3 天（含测试）
- 前端开发: 1 天
- 测试和优化: 1-2 天
- **总计**: 4-6 天

### 运维成本
- 服务器: 无额外成本（复用现有）
- 存储: 可忽略
- 带宽: 增加 < 5%

---

## 成功指标

- 搜索联想响应时间 < 100ms (P95)
- 采用率 > 30%（点击联想进入帖子）
- 搜索成功率提升 > 10%
- 用户满意度 > 4.0/5.0

---

## 参考资料

- [PostgreSQL Full Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [pg_trgm Extension](https://www.postgresql.org/docs/current/pgtrgm.html)
- [Elasticsearch Suggesters](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-suggesters.html)
- [jieba 中文分词](https://github.com/fxsjy/jieba)

---

**文档版本**: 1.0  
**创建日期**: 2025-11-25  
**负责人**: 前端团队  
**后端支持**: 待确认
