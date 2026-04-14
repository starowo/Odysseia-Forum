export interface SidebarChannelItem {
  id: string;
  name: string;
}

export interface SidebarChannelCategory {
  name: string;
  channels: SidebarChannelItem[];
}

export const GUILD_ID = '1134557553011998840';

export const CHANNEL_CATEGORIES: SidebarChannelCategory[] = [
  {
    name: '角色卡',
    channels: [
      { id: '1374474903981527082', name: '纯净区' },
      { id: '1374481342825238821', name: '男性向' },
      { id: '1374488912143061114', name: '女性向' },
      { id: '1374491326308946071', name: '全性向' },
      { id: '1374491950161330277', name: '其它区' },
      { id: '1235867354060034068', name: '档案馆-纯净区' },
      { id: '1381148770351452170', name: '档案馆-混沌区' },
      { id: '1374594860316885054', name: '深渊区' },
    ],
  },
  {
    name: '资源区',
    channels: [
      { id: '1233691226507575367', name: '世界书' },
      { id: '1240569535472472126', name: '插件区' },
      { id: '1376208053212545107', name: '工具区' },
      { id: '1134822069222264874', name: '预设区' },
      { id: '1234521076919308348', name: '酒馆美化' },
      { id: '1134717476505137215', name: '教程分享' },
    ],
  },
];

export const CHANNELS = Object.fromEntries(
  CHANNEL_CATEGORIES.flatMap((category) =>
    category.channels.map((channel) => [channel.id, channel.name] as const),
  ),
);
