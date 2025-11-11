// 主题配置文件 - 为多主题支持做准备

export interface Theme {
  name: string;
  colors: {
    // 背景色
    background: string;
    backgroundSecondary: string;
    backgroundTertiary: string;
    
    // 卡片色
    card: string;
    cardHover: string;
    
    // 文本色
    textPrimary: string;
    textSecondary: string;
    textTertiary: string;
    
    // 强调色
    accent: string;
    accentHover: string;
    
    // 链接色
    link: string;
    linkHover: string;
    
    // 边框色
    border: string;
    borderStrong: string;
    
    // 状态色
    success: string;
    warning: string;
    error: string;
    info: string;
  };
}

// Discord 深色主题（当前使用）
export const discordDarkTheme: Theme = {
  name: 'Discord Dark',
  colors: {
    // 背景色
    background: '#282a2e',
    backgroundSecondary: '#2b2d31',
    backgroundTertiary: '#1e1f22',
    
    // 卡片色
    card: '#1e1f22',
    cardHover: '#232428',
    
    // 文本色
    textPrimary: '#f2f3f5',
    textSecondary: '#b5bac1',
    textTertiary: '#949ba4',
    
    // 强调色
    accent: '#5865f2',
    accentHover: '#4752c4',
    
    // 链接色
    link: '#00a8fc',
    linkHover: '#00c7fc',
    
    // 边框色
    border: '#2b2d31',
    borderStrong: '#3f4147',
    
    // 状态色
    success: '#23a55a',
    warning: '#f0b232',
    error: '#f23f42',
    info: '#00a8fc',
  },
};

// Discord 浅色主题（预留）
export const discordLightTheme: Theme = {
  name: 'Discord Light',
  colors: {
    background: '#ffffff',
    backgroundSecondary: '#f2f3f5',
    backgroundTertiary: '#e3e5e8',
    
    card: '#ffffff',
    cardHover: '#f2f3f5',
    
    textPrimary: '#060607',
    textSecondary: '#4e5058',
    textTertiary: '#80848e',
    
    accent: '#5865f2',
    accentHover: '#4752c4',
    
    link: '#00a8fc',
    linkHover: '#0087d1',
    
    border: '#e3e5e8',
    borderStrong: '#d4d7dc',
    
    success: '#23a55a',
    warning: '#f0b232',
    error: '#f23f42',
    info: '#00a8fc',
  },
};

// 默认主题
export const defaultTheme = discordDarkTheme;

// 主题列表
export const themes = {
  dark: discordDarkTheme,
  light: discordLightTheme,
};

// 主题类型
export type ThemeName = keyof typeof themes;
