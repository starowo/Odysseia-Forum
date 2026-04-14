import {
  Monitor,
  Moon,
  Sun,
  type LucideIcon,
} from 'lucide-react';

import type { UserSettings } from '@/shared/lib/settings';
import defaultWinterBackground from '@/assets/images/background/winter.png';
import defaultSpringBackground from '@/assets/images/background/spring.png';
import defaultSpring2Background from '@/assets/images/background/spring2.png';
import defaultBannerBackground from '@/assets/images/banners/adfd891a-f9f7-4f9d-8d7c-975fb32a7f0d.png';

type ThemeOption = {
  id: UserSettings['theme'];
  label: string;
  icon: LucideIcon;
  themeKey:
    | 'discordDark'
    | 'discordLight'
    | 'claudeDark'
    | 'catppuccin'
    | 'nord'
    | 'everforest'
    | 'sakuraDay'
    | 'yozakuraNight'
    | 'tokyoNight'
    | null;
  description: string;
};

export const themeOptions: ThemeOption[] = [
  {
    id: 'discord-dark',
    label: 'Discord 深色',
    icon: Moon,
    themeKey: 'discordDark',
    description: '经典 Discord 暗色风格',
  },
  {
    id: 'discord-light',
    label: 'Discord 浅色',
    icon: Sun,
    themeKey: 'discordLight',
    description: '明亮的浅色主题',
  },
  {
    id: 'claude-dark',
    label: 'Claude 深色',
    icon: Moon,
    themeKey: 'claudeDark',
    description: '保留的经典深色主题',
  },
  {
    id: 'catppuccin',
    label: 'Catppuccin',
    icon: Moon,
    themeKey: 'catppuccin',
    description: '柔和高对比的社区经典',
  },
  {
    id: 'nord',
    label: 'Nord',
    icon: Moon,
    themeKey: 'nord',
    description: '冷调清晰的信息密度风格',
  },
  {
    id: 'everforest',
    label: 'Everforest',
    icon: Moon,
    themeKey: 'everforest',
    description: '护眼森林调，适合长时阅读',
  },
  {
    id: 'sakura-day',
    label: 'Sakura Day',
    icon: Sun,
    themeKey: 'sakuraDay',
    description: '春樱明朝风，淡粉与叶绿',
  },
  {
    id: 'yozakura-night',
    label: 'Yozakura Night',
    icon: Moon,
    themeKey: 'yozakuraNight',
    description: '夜樱霓光，冷调紫与冰蓝',
  },
  {
    id: 'tokyo-night',
    label: 'Tokyo Night',
    icon: Moon,
    themeKey: 'tokyoNight',
    description: '代码高亮感最强的夜色主题',
  },
  {
    id: 'auto',
    label: '跟随系统',
    icon: Monitor,
    themeKey: null,
    description: '根据系统深浅色自动切换',
  },
];

export const backgroundPresets = [
  {
    id: 'winter',
    label: 'Winter',
    description: '冷冽雪原',
    previewUrl: defaultWinterBackground,
  },
  {
    id: 'spring',
    label: 'Spring',
    description: '浅春枝影',
    previewUrl: defaultSpringBackground,
  },
  {
    id: 'spring-2',
    label: 'Spring 2',
    description: '偏暖花雾',
    previewUrl: defaultSpring2Background,
  },
  {
    id: 'banner',
    label: 'Banner',
    description: '站内主视觉',
    previewUrl: defaultBannerBackground,
  },
] as const;
