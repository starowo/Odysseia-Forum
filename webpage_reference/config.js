window.GUILD_ID = "123";

// 频道分类配置
window.CHANNEL_CATEGORIES = [
  {
    name: "分类1",
    channels: [
      { id: "122", name: "频道1" }
    ]
  },
  {
    name: "分类2",
    channels: [
      { id: "123", name: "频道2" }
    ]
  }
];

// 保持兼容性的扁平化频道列表
window.CHANNELS = {};
window.CHANNEL_CATEGORIES.forEach(category => {
  category.channels.forEach(channel => {
    window.CHANNELS[channel.id] = channel.name;
  });
});

window.CLIENT_ID = "123";
window.AUTH_URL = "http://localhost:10810/v1";