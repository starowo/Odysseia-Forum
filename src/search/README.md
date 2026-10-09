# 🔍 Search 模块

## 📖 简介
`search` 模块负责提供帖子（Thread）检索服务。

它支持标签（正选/反选）、作者、时间范围、数值区间（点赞/回复数）以及基于 jieba 分词的 SQLite FTS5 关键词搜索。此外，还实现了基于 UCB1 算法的综合推荐排序和子服务器频道映射虚拟标签功能。

本模块采用 **策略模式 (Strategy Pattern)** 的架构来复用底层 UI 和查询逻辑，方便未来扩展各种特定场景的搜索（如全局搜索、作者搜索、收藏搜索等）。

---

## 📂 目录结构与核心组件

```text
search/
├── cog.py                       # Discord Cog 入口，注册斜杠命令和上下文菜单。
├── search_service.py            # 查询服务：将 DTO/QO 转换为数据库查询。
├── channel_mapping_utils.py     # 频道映射工具：处理“虚拟标签”到“实际频道”的转换逻辑。
├── constants.py                 # 定义常量，如所有支持的排序方法 (SortMethod)。
│
├── strategies/                  # 🚀 搜索策略层 (Strategy Pattern)
│   ├── search_strategy.py       # 策略基类 (定义获取标题、可用标签、过滤组件的接口)。
│   ├── default_search_strategy.py # 默认的全局/频道搜索策略。
│   ├── author_search_strategy.py  # 特定作者帖子的搜索策略。
│   └── collection_search_strategy.py # 用户收藏帖子的搜索策略。
│
├── views/                       # 🖥️ 交互视图层 (Discord UI Views)
│   ├── generic_search_view.py   # 核心筛选 UI 面板 (承载各种过滤条件的组合)。
│   ├── results_view.py          # 搜索结果的分页按钮与跳转逻辑。
│   ├── channel_selection_view.py# 全局搜索时的频道前置选择 UI。
│   ├── combined_search_view.py  # 将条件面板和分页面板组合在一起的容器视图。
│   └── thread_embed_builder.py  # 将数据库帖子对象转换为最终展示的 Discord Embed 。
│
├── components/                  # 🧩 可复用的 UI 组件库 (Buttons, Selects, Modals)。
│   ├── continue_button.py       # 视图超时后的“继续搜索”状态恢复按钮。
│   ├── keyword_modal.py         # 关键词设置模态框及触发按钮 (含包含/排除/豁免词配置)。
│   ├── number_range_modal.py    # 反应数/回复数等数值区间设置的模态框。
│   ├── search_button.py         # 执行搜索操作的点击按钮组件。
│   ├── sort_method_select.py    # 排序算法选择下拉框 (综合、时间、热度及自定义基准)。
│   ├── sort_order_button.py     # 升序(asc)/降序(desc)切换按钮。
│   ├── tag_logic_button.py      # 多标签匹配逻辑切换按钮 (同时满足 AND / 任一满足 OR)。
│   └── tag_page_button.py       # 标签选择下拉框的上一页/下一页翻页组件。
│
├── qo/                          # 📦 查询对象 (Query Objects)
│   └── thread_search.py         # ThreadSearchQuery: 封装传给数据库层的标准查询条件。
│
└── dto/                         # 📦 数据传输对象 (Data Transfer Objects)
    ├── search_state.py          # SearchStateDTO: 保存当前用户在 UI 上的所有筛选状态。
    └── channel_mapping_resolution.py # 记录虚拟标签解析后的结果。
```

---

## ⚙️ 核心机制说明

### 1. 数据的流转生命周期
一次完整的搜索请求生命周期如下：
1. 触发交互: 用户点击按钮或使用命令 (在 `cog.py` 中捕获)。
2. 初始化状态: 生成 `SearchStateDTO`（会融合用户保存在数据库的默认搜索偏好）。
3. 分配策略: 根据搜索入口实例化对应的 `SearchStrategy` (如 `DefaultSearchStrategy`)。
4. 渲染 UI: 实例化 `GenericSearchView`，策略类负责提供 UI 组件 (标签下拉框、排序按钮等)。
5. 构建查询: 当用户调整筛选条件时，视图根据 `SearchStateDTO` 生成 `ThreadSearchQuery` (QO)。
6. 虚拟标签解析: `channel_mapping_utils.py` 拦截查询，将虚拟标签转换为真实的 `channel_ids` 过滤。
7. 数据库执行: `SearchService` 将 QO 转换为 SQL：
   - 使用 FTS5 执行关键词 MATCH (jieba 分词)。
   - 拼接 SQLAlchemy `where` 条件 (时间、数值、标签)。
   - 应用排序。
8. 结果渲染: `ThreadEmbedBuilder` 组装 Embed 列表并交由 `CombinedSearchView` 展示。

### 2. 全文搜索 (FTS5 + Jieba)
关键词搜索利用了 SQLite 的 FTS5 虚拟表，并挂载了 Jieba-rs 结巴分词。
- 逻辑实现在 `SearchService._execute_search` 中。
- 支持正选词、反选词（以逗号或斜杠分割）。
- 实现了**豁免词机制** (exemption_markers)，如搜索排除了“暴力”，但帖子写了“禁暴力”，可通过 `NEAR` 语法予以豁免。

### 3. UCB1 综合推荐算法
默认的“综合排序”不是按时间，而是为了平衡**热门内容**和**新内容**的曝光。
公式：$Score = W \times \frac{x}{n} + C \times \sqrt{\frac{\ln(N)}{n}}$
- $x$ = 帖子获得的总反应数 (Reaction Count)
- $n$ = 该帖子在搜索中的总展示次数 (Display Count)
- $N$ = 全局总展示次数
- $W$ 和 $C$ 为在 `BotConfig` 中可调的权重参数。
*(注：由于使用了 UCB1，每次显示搜索结果都会触发 `ImpressionCacheService` 异步增加帖子的展示次数)*。

[UCB1 算法详细解释](..../docs/RANKING_ALGORITHM.md)

### 4. 频道映射与虚拟标签
为了解决分服架构下的搜索需求，我们在 `config.json` 中配置了 `channel_mappings`。
`ChannelMappingUtils` 会在查询前执行拦截：
- 如果用户选了**虚拟标签**（如“分服-纯文字”映射了A频道），查询时会剔除该虚拟标签，并将搜索范围限定在 A 频道。
- 这部分逻辑较为复杂，修改 `channel_mapping_utils.py` 时请务必编写或运行对应的测试用例。

---

## 🛠️ 协作者开发指南 (How-To)

### ❓ 如何添加一个新的“排序方式”？
1. 在 `constants.py` 的 `SortMethod` 枚举中注册你的新排序项。
2. 在 `qo/thread_search.py` (QO) 和 `dto/search_state.py` (DTO) 中确认默认值支持你的排序。
3. 在 `search_service.py` 的 `search_threads_with_count` 方法的结尾处，添加你的排序字段 (`order_by`) 逻辑。

### ❓ 如何添加一个新的“筛选条件”？
1. **DTO & QO**: 在 `SearchStateDTO` 和 `ThreadSearchQuery` 中增加字段。
2. **UI 层**: 
   - 在 `components/` 中新建一个 UI 组件 (Button, Select 或 Modal)。
   - 查看对应 Strategy 类 (`strategies/*.py`) 的 `get_filter_components` 方法，思考如何将你的组件挂载到 UI 布局中。
   - 在 `GenericSearchView` 中增加一个 `on_xxx_change` 回调函数来更新 State 并触发重搜。
3. **数据库层**: 在 `search_service.py` 中将新字段解析为 SQLAlchemy 的 `filters.append(...)`。

### ❓ 如何创建一个新的“搜索场景” (比如只搜带有特定图片的帖子)?

1. 在 `strategies/` 目录下新建 `ImageSearchStrategy(SearchStrategy)`。
2. 重写 `modify_query(self, query)` 方法，在发送给数据库前强制修改 query 条件。
3. 重写 `get_filter_components`，决定这个场景下用户能看到哪些筛选按钮。
4. 在入口处 (如 `cog.py`) 实例化 `GenericSearchView` 时传入你的新策略即可。

---

## ⚠️ 注意事项

1. **API 限流保护 (`safe_defer`)**
   Discord UI 交互只有 3 秒响应时间。在任何会导致数据库阻塞或外部调用的操作前，务必调用 `await safe_defer(interaction)` 占坑。
2. **分页状态保持**
   当用户在“标签选择”里翻页或点击“下一页”时，所有之前的勾选状态**必须保持**。这点在 `shared/views/tag_select.py` 中有特殊处理，修改下拉框逻辑时请当心。
3. **高并发下的展现统计**
   不要在搜索逻辑中直接执行 `UPDATE thread SET display_count += 1`，这会导致数据库严重的锁竞争。请统一调用全局的 `bot.impression_cache_service.increment()`，它会在内存中缓冲并定时批量 Flush 到数据库。
4. **JavaScript ID 精度丢失问题**
   Discord 的 Snowflake ID 是超大整数。在 DTO 传给索引页前端渲染或者序列化时，请务必使用 `str(id)` 转换为字符串处理，否则在某些前端视图或 JSON 序列化中最后几位会变成 `0`。
