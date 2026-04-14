import { useEffect, useMemo, useState } from 'react';
import { themes, type ThemeName, type Theme } from '@/shared/styles/themes';
import { useSettings, useThemeSettings } from '@/shared/hooks/useSettings';
import type { UserSettings } from '@/shared/lib/settings';

const LIGHT_THEME_NAMES: ThemeName[] = ['discordLight', 'sakuraDay'];

function isLightThemeName(themeName: ThemeName) {
  return LIGHT_THEME_NAMES.includes(themeName);
}

// 将用户设置中的 theme 字段映射到具体的 ThemeName
function mapSettingsThemeToKey(
  settingsTheme: UserSettings['theme'],
  systemPrefersDark: boolean
): ThemeName {
  switch (settingsTheme) {
    case 'discord-dark':
      return 'discordDark';
    case 'discord-light':
      return 'discordLight';
    case 'claude-dark':
      return 'claudeDark';
    case 'tokyo-night':
      return 'tokyoNight';
    case 'catppuccin':
      return 'catppuccin';
    case 'nord':
      return 'nord';
    case 'everforest':
      return 'everforest';
    case 'sakura-day':
      return 'sakuraDay';
    case 'yozakura-night':
      return 'yozakuraNight';
    case 'auto':
    default:
      // 自动模式下，跟随系统：深色用 Claude Dark，浅色用 Discord Light
      // 统一把默认暗色升级到新主题体系
      return systemPrefersDark ? 'claudeDark' : 'discordLight';
  }
}

// 将 ThemeName 映射回用户设置中的 theme 值
function mapThemeNameToSettings(themeName: ThemeName): UserSettings['theme'] {
  switch (themeName) {
    case 'discordDark':
      return 'discord-dark';
    case 'discordLight':
      return 'discord-light';
    case 'claudeDark':
      return 'claude-dark';
    case 'tokyoNight':
      return 'tokyo-night';
    case 'catppuccin':
      return 'catppuccin';
    case 'nord':
      return 'nord';
    case 'everforest':
      return 'everforest';
    case 'sakuraDay':
      return 'sakura-day';
    case 'yozakuraNight':
      return 'yozakura-night';
    default:
      return 'claude-dark';
  }
}

export function useTheme() {
  const settings = useThemeSettings();
  const { updateSettings } = useSettings();

  // 监听系统深色模式偏好
  const [systemPrefersDark, setSystemPrefersDark] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (event: MediaQueryListEvent) => {
      setSystemPrefersDark(event.matches);
    };

    // 初始化
    setSystemPrefersDark(mediaQuery.matches);

    mediaQuery.addEventListener('change', handleChange);
    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, []);

  // 计算当前实际使用的主题（考虑 auto + 系统偏好）
  const currentThemeName = useMemo<ThemeName>(
    () => mapSettingsThemeToKey(settings.theme, systemPrefersDark),
    [settings.theme, systemPrefersDark]
  );

  const theme: Theme = themes[currentThemeName];

  // 切换主题：只在浅色/深色之间切换，不轮播整套主题列表
  const toggleTheme = () => {
    const nextSettingsTheme: UserSettings['theme'] = isLightThemeName(currentThemeName)
      ? 'claude-dark'
      : 'discord-light';

    updateSettings({ theme: nextSettingsTheme });
  };

  // 设置指定主题（来自设置页、颜色盘等）
  const setTheme = (themeName: ThemeName) => {
    const next = mapThemeNameToSettings(themeName);
    updateSettings({ theme: next });
  };

  return {
    theme,
    currentTheme: currentThemeName,
    isDarkTheme: !isLightThemeName(currentThemeName),
    toggleTheme,
    setTheme,
  };
}
