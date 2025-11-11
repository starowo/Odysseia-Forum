// 设置相关的类型定义和存储管理

export interface UserSettings {
  fontSize: 'small' | 'medium' | 'large';
  cardSize: 'compact' | 'normal' | 'large';
  layoutMode: 'grid' | 'list';
  compactMode: boolean;
  theme: 'light' | 'dark' | 'auto';
  notifications: {
    newPosts: boolean;
    replies: boolean;
    mentions: boolean;
  };
}

const SETTINGS_KEY = 'odysseia_user_settings';

// 默认设置
const defaultSettings: UserSettings = {
  fontSize: 'medium',
  cardSize: 'normal',
  layoutMode: 'grid',
  compactMode: false,
  theme: 'dark',
  notifications: {
    newPosts: true,
    replies: true,
    mentions: true,
  },
};

// 获取用户设置
export function getUserSettings(): UserSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // 合并默认设置，确保新增的设置项有默认值
      return { ...defaultSettings, ...parsed };
    }
  } catch (error) {
    console.error('Failed to load user settings:', error);
  }
  return defaultSettings;
}

// 保存用户设置
export function saveUserSettings(settings: UserSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    // 触发自定义事件，通知其他组件设置已更新
    window.dispatchEvent(new CustomEvent('settingsChanged', { detail: settings }));
  } catch (error) {
    console.error('Failed to save user settings:', error);
  }
}

// 更新部分设置
export function updateUserSettings(updates: Partial<UserSettings>): void {
  const current = getUserSettings();
  const updated = { ...current, ...updates };
  saveUserSettings(updated);
}

// 重置设置
export function resetUserSettings(): void {
  saveUserSettings(defaultSettings);
}

// 字体大小映射
export const fontSizeMap = {
  small: {
    title: 'text-base', // 16px
    content: 'text-sm', // 14px
    meta: 'text-xs', // 12px
  },
  medium: {
    title: 'text-lg', // 18px
    content: 'text-sm', // 14px
    meta: 'text-xs', // 12px
  },
  large: {
    title: 'text-xl', // 20px
    content: 'text-base', // 16px
    meta: 'text-sm', // 14px
  },
};

// 卡片大小映射
export const cardSizeMap = {
  compact: {
    padding: 'p-2',
    gap: 'gap-2',
    imageHeight: 'aspect-[16/9]',
    titleLines: 'line-clamp-1',
    contentLines: 'line-clamp-2',
  },
  normal: {
    padding: 'p-3',
    gap: 'gap-3',
    imageHeight: 'aspect-[4/3]',
    titleLines: 'line-clamp-2',
    contentLines: 'line-clamp-3',
  },
  large: {
    padding: 'p-4',
    gap: 'gap-4',
    imageHeight: 'aspect-[3/2]',
    titleLines: 'line-clamp-3',
    contentLines: 'line-clamp-4',
  },
};
