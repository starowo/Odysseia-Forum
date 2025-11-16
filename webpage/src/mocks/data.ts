/**
 * 本文件只用于 MSW mock，本地开发时通过 VITE_API_MOCKING=true 启用。
 * 生产环境不会被打包到真实 API 逻辑中。
 */

 // 模拟频道数据（覆盖技术 / AI / 日常等几类）
export const MOCK_CHANNELS = [
  {
    name: '技术区',
    channels: [
      { id: '1', name: '前端开发 · Web UI' },
      { id: '2', name: '后端交流 · API & 服务' },
      { id: '3', name: '基础设施 · DevOps' },
    ],
  },
  {
    name: 'AI 研究',
    channels: [
      { id: '4', name: '大模型 · LLM' },
      { id: '5', name: 'Prompt 设计实验室' },
      { id: '6', name: 'Paper 复现与 Benchmark' },
    ],
  },
  {
    name: '项目区',
    channels: [
      { id: '7', name: '开源项目展示' },
      { id: '8', name: '问题求助 & Debug' },
    ],
  },
  {
    name: '生活区',
    channels: [
      { id: '9', name: '摸鱼吹水' },
      { id: '10', name: '兴趣爱好分享' },
    ],
  },
];

// 与后端 /v1/meta/channels 对齐的扁平频道列表
// 生产环境中该接口返回 Channel[]，这里只是用 MOCK_CHANNELS 展开模拟
export const MOCK_META_CHANNELS = MOCK_CHANNELS.flatMap((category) =>
  category.channels.map((ch) => ({
    id: ch.id,
    name: ch.name,
  }))
);

// 模拟标签数据：技术 + 场景 + 状态
export const MOCK_TAGS = [
  { id: '101', name: 'React', color: '#61DAFB' },
  { id: '102', name: 'Vue', color: '#4FC08D' },
  { id: '103', name: 'Node.js', color: '#68A063' },
  { id: '104', name: 'Python', color: '#306998' },
  { id: '105', name: 'Rust', color: '#dea584' },
  { id: '106', name: 'LLM', color: '#a855f7' },
  { id: '107', name: 'Prompt', color: '#ec4899' },
  { id: '108', name: '部署', color: '#22c55e' },
  { id: '109', name: '已解决', color: '#16a34a' },
  { id: '110', name: '未解决', color: '#f97316' },
  { id: '111', name: '摸鱼', color: '#fbbf24' },
];

const TITLE_TEMPLATES = [
  (i: number) => `【实战】用 React 做一个高性能搜索列表 (${i})`,
  (i: number) => `请教一下：后端分页 + 前端缓存应该怎么设计？#架构 ${i}`,
  (i: number) => `分享一个最近踩坑的部署故事，差点把生产干崩 (${i})`,
  (i: number) => `LLM 对话里如何优雅地控制回复长度？Prompt 讨论 ${i}`,
  (i: number) => `今天的摸鱼日报：我在 ${i} 分钟内什么都没干`,
  (i: number) => `【长文】从 0 到 1 写一个搜索服务的完整思路（含索引 & 排序） (${i})`,
];

const EXCERPT_SHORT = [
  '一行代码解决的小问题，但背后有点意思。',
  '纯提问，求大佬们指路。',
  '简单记录一下过程，怕以后自己忘了。',
];

const EXCERPT_LONG = [
  // 带 Markdown 语法的长文预览，用于测试 MarkdownText 渲染
  '**这是一段带 Markdown 的长文预览**，用于测试 `MarkdownText` 组件在卡片展开时的表现。\n\n' +
    '- 支持 **粗体** / _斜体_\n' +
    '- 行内 `code` 片段\n' +
    '- [外部链接](https://example.com)\n\n' +
    '> 这是一个引用块，用来模拟论坛帖子里的引用回复场景。',
  '最近在折腾一个小项目，涉及到前端渲染性能优化、后端分页查询、全文检索以及缓存策略等一整套东西。\n\n' +
    '这篇帖子详细记录了我从需求分析到落地实现的完整过程，如果你也在做类似的事情，或许能给你一点启发。\n\n' +
    '`Tip`: 如果你看到这里，说明 **Markdown 渲染已经生效了**。',
  '# 一、LLM + 传统搜索的混合检索实践\n\n' +
    '这条帖子主要是想讨论一下在使用大模型（LLM）的时候，如何结合传统的搜索引擎做一个混合检索系统。\n\n' +
    '包括：\n' +
    '- 向量检索\n' +
    '- 关键词过滤\n' +
    '- 排序权重调优\n\n' +
    '> 整体会稍微硬核一点，但我尽量写得通俗易懂，方便入门。',
];

const SUPER_LONG_MARKDOWN =
  '# 超长 Markdown 示例\n\n' +
  '这是一条专门用于本地开发环境的「超长帖子内容」。它会被注入到部分 mock 线程中，用来测试以下几件事：\n\n' +
  '1. 双击卡片之后，内容区域是否真正切换到了 *MarkdownText* 渲染，而不是继续走摘要的行数截断逻辑。\n' +
  '2. 在内容非常长（接近几千字）的时候，滚动条与卡片的布局是否正常，长文是否可以完整滚动查看。\n' +
  '3. 链接、代码块、引用、多级标题在深色/浅色主题下的可读性是否足够好。\n\n' +
  '---\n\n' +
  '## 一、基础 Markdown 元素\n\n' +
  '我们先来罗列一些常见的 Markdown 语法：\n\n' +
  '- **粗体文字**：用于强调关键信息\n' +
  '- _斜体文字_：用于次要强调\n' +
  '- `行内代码`：例如 `SELECT * FROM threads WHERE ...`\n' +
  '- [外部链接](https://example.com)：用于跳转到外部文档\n' +
  '- > 引用块：用于回复或摘录原帖内容\n\n' +
  '接下来是一段代码块：\n\n' +
  '```ts\n' +
  'function searchThreads(query: string) {\n' +
  "  return fetch(`/v1/search`, { method: 'POST', body: JSON.stringify({ keywords: query }) });\n" +
  '}\n' +
  '```\n\n' +
  '## 二、模拟真实论坛帖子的长文结构\n\n' +
  '真实环境里的帖子往往会非常长，可能包含：需求分析、方案设计、踩坑记录、性能数据、结论与反思等多个部分。这里我们用几段冗长的中文文字来模拟这种场景。\n\n' +
  '首先是一个「故事型」的段落，用来测试连续多段文本的布局效果：\n\n' +
  '> 某天凌晨两点，管理员发现搜索服务的延迟突然飙升，于是大家一边抓着咖啡，一边开始排查。从索引结构、SQL 语句、缓存命中率，到磁盘 IO、网络带宽，所有能想到的地方都检查了一遍。最终发现问题竟然出在一个看似无害的 debug 日志上——它在高并发场景下疯狂刷盘，拖慢了整条链路。\n\n' +
  '然后是一些「技术说明」型的段落：\n\n' +
  '在这个 mock 长文里，我们不会真的给出一套完整的架构设计，但会刻意把段落写得比较长，以测试换行与行距。你可以随意拖动滚动条，感受在卡片展开之后，长文阅读的体验是否足够顺畅。如果感觉某些行距、字号、行宽不合适，可以直接在全局的 `.od-md` 样式里调整。\n\n' +
  '## 三、总结\n\n' +
  '如果你能顺利滑到这里，说明：\n\n' +
  '- 双击卡片展开逻辑工作正常\n' +
  '- Markdown 渲染工作正常\n' +
  '- 滚动区域高度设置基本合理\n\n' +
  '接下来你可以根据自己的审美继续微调：\n\n' +
  '- 增加或减弱卡片上浮效果\n' +
  '- 调整代码块与引用块的背景色/边框色\n' +
  '- 调整链接颜色与 hover 状态\n\n' +
  '总之，这只是本地 mock，不会进入生产环境，你可以放心地把它写得非常「啰嗦」，只要有利于调 UI 就行。';

// 工具：从标签表中随机选出 1~3 个标签
function pickRandomTags(): string[] {
  const count = 1 + Math.floor(Math.random() * 3); // 1~3
  const shuffled = [...MOCK_TAGS].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count).map((t) => t.name);
}

// 工具：生成不同长度的摘要；有些帖子没有摘要
function pickExcerpt(i: number): string | undefined {
  const mod = i % 4;
  if (mod === 0) {
    return EXCERPT_SHORT[i % EXCERPT_SHORT.length];
  }
  if (mod === 1) {
    return EXCERPT_LONG[i % EXCERPT_LONG.length];
  }
  if (mod === 2) {
    return '一句话概括问题：感觉写得没问题，但就是跑不起来。';
  }
  // 留空，测试没有摘要的情况
  return undefined;
}

 // 模拟帖子数据：混合不同频道、tag、多种文案
export const MOCK_THREADS = Array.from({ length: 80 }, (_, i) => {
  const channelCategory = MOCK_CHANNELS[i % MOCK_CHANNELS.length];
  const channel = channelCategory.channels[i % channelCategory.channels.length];

  const createdAt = new Date(Date.now() - i * 3_600_000); // 每条相差 1 小时
  const lastActive = new Date(createdAt.getTime() + Math.floor(Math.random() * 2_400_000)); // +0~40 分钟

  const titleTemplate = TITLE_TEMPLATES[i % TITLE_TEMPLATES.length];

  const thumbnail =
    i % 3 === 0
      ? `https://picsum.photos/seed/thread-${i}/400/200`
      : i % 5 === 0
        ? `https://picsum.photos/seed/thread-wide-${i}/600/300`
        : null;

  const tags = pickRandomTags();

  return {
    thread_id: `thread-${i + 1}`,
    title: titleTemplate(i + 1),
    author: {
      id: `user-${i % 7}`,
      name: `用户${i % 7}`,
      display_name: `用户${i % 7}`,
    },
    channel_id: channel.id,
    guild_id: 'mock-guild-id',
    tags,
    first_message_excerpt: pickExcerpt(i + 1),
    created_at: createdAt.toISOString(),
    last_comment_time: lastActive.toISOString(),
    last_active_at: lastActive.toISOString(),
    reaction_count: Math.floor(Math.random() * 200),
    reply_count: Math.floor(Math.random() * 80),
    thumbnail_url: thumbnail,
  };
});

// 约定：前 12 条帖子视为“已关注”，其中前 3 条有更新
export const FOLLOWED_THREAD_IDS = MOCK_THREADS.slice(0, 12).map((t) => t.thread_id);
export const UPDATED_THREAD_IDS = FOLLOWED_THREAD_IDS.slice(0, 3);