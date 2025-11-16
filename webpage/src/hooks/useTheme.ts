import { useEffect, useMemo, useState } from 'react';
import { themes, type ThemeName, type Theme } from '@/styles/themes';
import { useSettings } from '@/hooks/useSettings';
import type { UserSettings } from '@/lib/settings';

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
    case 'tweak-gray-dark':
      return 'tweakGrayDark';
    case 'tweak-gray-light':
      return 'tweakGrayLight';
    case 'auto':
    default:
      // 自动模式下，跟随系统：深色用 Discord Dark，浅色用 Discord Light
      return systemPrefersDark ? 'discordDark' : 'discordLight';
  }
}

// 将 ThemeName 映射回用户设置中的 theme 值
function mapThemeNameToSettings(themeName: ThemeName): UserSettings['theme'] {
  switch (themeName) {
    case 'discordDark':
      return 'discord-dark';
    case 'discordLight':
      return 'discord-light';
    case 'tweakGrayDark':
      return 'tweak-gray-dark';
    case 'tweakGrayLight':
      return 'tweak-gray-light';
    default:
      return 'discord-dark';
  }
}

export function useTheme() {
  const { settings, updateSettings } = useSettings();

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

  // 切换主题：在当前系列的 Light/Dark 之间切换
  const toggleTheme = () => {
    const nextSettingsTheme: UserSettings['theme'] =
      currentThemeName === 'discordDark'
        ? 'discord-light'
        : currentThemeName === 'discordLight'
        ? 'discord-dark'
        : currentThemeName === 'tweakGrayDark'
        ? 'tweak-gray-light'
        : currentThemeName === 'tweakGrayLight'
        ? 'tweak-gray-dark'
        : 'discord-dark';

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
    toggleTheme,
    setTheme,
  };
}
