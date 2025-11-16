// 模拟频道数据
export const MOCK_CHANNELS = [
  {
    category: '技术区',
    channels: [
      { id: '1', name: '前端开发' },
      { id: '2', name: '后端交流' },
    ],
  },
  {
    category: '生活区',
    channels: [
      { id: '3', name: '摸鱼吹水' },
      { id: '4', name: '兴趣爱好' },
    ],
  },
];

// 模拟标签数据
export const MOCK_TAGS = [
  { id: '101', name: 'React', color: '#61DAFB' },
  { id: '102', name: 'Vue', color: '#4FC08D' },
  { id: '103', name: 'Node.js', color: '#68A063' },
  { id: '104', name: 'Python', color: '#306998' },
  { id: '105', name: '摸鱼', color: '#F0AD4E' },
];

// 模拟帖子数据
export const MOCK_THREADS = Array.from({ length: 50 }, (_, i) => ({
  thread_id: `thread-${i + 1}`,
  title: `这是第 ${i + 1} 个模拟帖子标题`,
  author: {
    id: `user-${i % 5}`,
    name: `用户${i % 5}`,
    display_name: `用户${i % 5}`,
  },
  channel_id: String((i % 4) + 1),
  guild_id: 'mock-guild-id',
  tags: [MOCK_TAGS[i % 5].name, MOCK_TAGS[(i + 1) % 5].name],
  first_message_excerpt: '这是帖子的内容预览，展示了帖子的前几个字，用来吸引用户点击查看详情...',
  created_at: new Date(Date.now() - i * 3600000).toISOString(),
  last_comment_time: new Date(Date.now() - i * 1800000).toISOString(),
  reaction_count: Math.floor(Math.random() * 100),
  reply_count: Math.floor(Math.random() * 50),
  thumbnail_url: i % 3 === 0 ? `https://picsum.photos/seed/${i}/400/200` : null, // 每隔3个帖子给一个随机图片
}));