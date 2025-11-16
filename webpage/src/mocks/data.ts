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
  '这是一个比较长的内容预览，我们会故意写得稍微长一点，用来测试卡片在不同屏幕宽度下的文本截断表现。' +
    '如果在窄屏上显示，应该只展示前面一两行，而在桌面宽屏上则会看到更多信息，从而方便快速判断帖子的价值。',
  '最近在折腾一个小项目，涉及到前端渲染性能优化、后端分页查询、全文检索以及缓存策略等一整套东西。' +
    '这篇帖子详细记录了我从需求分析到落地实现的完整过程，如果你也在做类似的事情，或许能给你一点启发。',
  '这条帖子主要是想讨论一下在使用大模型（LLM）的时候，如何结合传统的搜索引擎做一个混合检索系统。' +
    '包括向量检索、关键词过滤、权重调优等话题，会比较硬核一点，但我尽量写得通俗易懂。',
];

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