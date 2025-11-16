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

/**
 * Tweak 灰调主题（原有一深一浅）
 */
export const tweakGrayDarkTheme: Theme = {
  name: 'Tweak Gray Dark',
  colors: {
    // 背景色（整体偏灰的深色）
    background: 'oklch(0.2046 0 0)',            // --background
    backgroundSecondary: 'oklch(0.2393 0 0)',    // --muted
    backgroundTertiary: 'oklch(0.2686 0 0)',     // --secondary

    // 卡片
    card: 'oklch(0.2686 0 0)',                  // --card
    cardHover: 'oklch(0.3715 0 0)',             // --border 作为 hover 提升

    // 文本
    textPrimary: 'oklch(0.9219 0 0)',           // --foreground
    textSecondary: 'oklch(0.7155 0 0)',         // --muted-foreground
    textTertiary: 'oklch(0.5510 0.0234 264.3637)', // 取接近的中灰

    // 强调色
    accent: 'oklch(0.6231 0.1880 259.8145)',    // --primary
    accentHover: 'oklch(0.5461 0.2152 262.8809)', // chart-2 略深

    // 链接
    link: 'oklch(0.7137 0.1434 254.6240)',      // chart-1
    linkHover: 'oklch(0.6231 0.1880 259.8145)', // primary

    // 边框
    border: 'oklch(0.3715 0 0)',                // --border
    borderStrong: 'oklch(0.2686 0 0)',          // 再深一点

    // 状态色
    success: 'oklch(0.7137 0.1434 254.6240)',   // 使用 chart-1 作为信息/成功色
    warning: 'oklch(0.8823 0.0571 254.1284)',   // accent-foreground 近似
    error: 'oklch(0.6368 0.2078 25.3313)',      // --destructive
    info: 'oklch(0.6231 0.1880 259.8145)',      // primary 作为信息色
  },
};

// Tweak 灰调浅色主题（来自 tweakcn :root 配色）
export const tweakGrayLightTheme: Theme = {
  name: 'Tweak Gray Light',
  colors: {
    // 背景色
    background: 'oklch(1.0000 0 0)',            // --background
    backgroundSecondary: 'oklch(0.9846 0.0017 247.8389)', // --muted
    backgroundTertiary: 'oklch(0.9670 0.0029 264.5419)',  // --secondary

    // 卡片
    card: 'oklch(1.0000 0 0)',                  // --card
    cardHover: 'oklch(0.9514 0.0250 236.8242)', // --accent

    // 文本
    textPrimary: 'oklch(0.3211 0 0)',           // --foreground
    textSecondary: 'oklch(0.5510 0.0234 264.3637)', // --muted-foreground
    textTertiary: 'oklch(0.4461 0.0263 256.8018)',   // secondary-foreground

    // 强调色
    accent: 'oklch(0.6231 0.1880 259.8145)',    // --primary
    accentHover: 'oklch(0.5461 0.2152 262.8809)', // chart-2

    // 链接
    link: 'oklch(0.4882 0.2172 264.3763)',      // chart-3
    linkHover: 'oklch(0.4244 0.1809 265.6377)', // chart-4

    // 边框
    border: 'oklch(0.9276 0.0058 264.5313)',    // --border
    borderStrong: 'oklch(0.8840 0.0100 260)',   // 稍微加深一点（手动估计）

    // 状态色
    success: 'oklch(0.6231 0.1880 259.8145)',   // primary 复用
    warning: 'oklch(0.6368 0.2078 25.3313)',    // destructive 作为警示色
    error: 'oklch(0.6368 0.2078 25.3313)',      // 同上
    info: 'oklch(0.3791 0.1378 265.5222)',      // chart-5
  },
};

/**
 * Paper 纸感主题（淡黄色纸张风格）
 * 复用了你给的 :root / .dark 配色，映射到现有 Theme 结构。
 */

// 深色纸感主题（对应 .dark）
export const paperDarkTheme: Theme = {
  name: 'Paper Dark',
  colors: {
    // 背景：整体偏深的暖灰
    background: 'oklch(0.2679 0.0036 106.6427)',              // --background
    backgroundSecondary: 'oklch(0.2357 0.0024 67.7077)',      // --sidebar
    backgroundTertiary: 'oklch(0.2213 0.0038 106.7070)',      // --muted

    // 卡片
    card: 'oklch(0.2679 0.0036 106.6427)',                    // --card
    cardHover: 'oklch(0.3085 0.0035 106.6039)',               // --popover

    // 文本
    textPrimary: 'oklch(0.8074 0.0142 93.0137)',              // --foreground
    textSecondary: 'oklch(0.7713 0.0169 99.0657)',            // --muted-foreground
    textTertiary: 'oklch(0.8074 0.0142 93.0137)',             // 轻微变化不大，可后续微调

    // 强调色（主按钮、选中状态）
    accent: 'oklch(0.6724 0.1308 38.7559)',                   // --primary
    accentHover: 'oklch(0.5583 0.1276 42.9956)',              // --chart-1 略深

    // 链接颜色（偏冷一点）
    link: 'oklch(0.6898 0.1581 290.4107)',                    // --chart-2
    linkHover: 'oklch(0.3074 0.0516 289.3230)',               // --chart-4

    // 边框
    border: 'oklch(0.3618 0.0101 106.8928)',                  // --border
    borderStrong: 'oklch(0.4336 0.0113 100.2195)',            // --input 稍亮一点

    // 状态色（先用主色系占位，后面你可以慢慢打磨）
    success: 'oklch(0.6898 0.1581 290.4107)',                 // 冷色成功
    warning: 'oklch(0.8816 0.0276 93.1280)',                  // --chart-3
    error: 'oklch(0.6368 0.2078 25.3313)',                    // --destructive
    info: 'oklch(0.6724 0.1308 38.7559)',                     // primary 作为信息色
  },
};

// 浅色纸感主题（对应 :root）
export const paperLightTheme: Theme = {
  name: 'Paper Light',
  colors: {
    // 背景：淡黄色纸张
    background: 'oklch(0.9818 0.0054 95.0986)',               // --background
    backgroundSecondary: 'oklch(0.9663 0.0080 98.8792)',      // --sidebar
    backgroundTertiary: 'oklch(0.9341 0.0153 90.2390)',       // --muted

    // 卡片
    card: 'oklch(0.9818 0.0054 95.0986)',                     // --card
    cardHover: 'oklch(0.9245 0.0138 92.9892)',                // --secondary

    // 文本
    textPrimary: 'oklch(0.3438 0.0269 95.7226)',              // --foreground
    textSecondary: 'oklch(0.6059 0.0075 97.4233)',            // --muted-foreground
    textTertiary: 'oklch(0.4334 0.0177 98.6048)',             // --secondary-foreground

    // 强调色（暖橙主色）
    accent: 'oklch(0.6171 0.1375 39.0427)',                   // --primary
    accentHover: 'oklch(0.5583 0.1276 42.9956)',              // --chart-1 略深

    // 链接颜色（稍冷一点，便于区分）
    link: 'oklch(0.6898 0.1581 290.4107)',                    // --chart-2
    linkHover: 'oklch(0.8822 0.0403 298.1792)',               // --chart-4

    // 边框
    border: 'oklch(0.8847 0.0069 97.3627)',                   // --border
    borderStrong: 'oklch(0.7621 0.0156 98.3528)',             // --input 稍深

    // 状态色
    success: 'oklch(0.6171 0.1375 39.0427)',                  // primary 复用
    warning: 'oklch(0.8816 0.0276 93.1280)',                  // --chart-3
    error: 'oklch(0.6368 0.2078 25.3313)',                    // --destructive
    info: 'oklch(0.6898 0.1581 290.4107)',                    // 冷色信息
  },
};

// 默认主题
export const defaultTheme = discordDarkTheme;

 // 主题列表（6 套主题）
export const themes = {
  discordDark: discordDarkTheme,
  discordLight: discordLightTheme,
  tweakGrayDark: tweakGrayDarkTheme,
  tweakGrayLight: tweakGrayLightTheme,
  paperDark: paperDarkTheme,
  paperLight: paperLightTheme,
} as const;

// 主题类型
export type ThemeName = keyof typeof themes;
