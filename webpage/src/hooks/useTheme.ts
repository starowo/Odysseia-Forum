import { useState, useEffect } from 'react';
import { themes, type ThemeName, type Theme } from '@/styles/themes';

const THEME_STORAGE_KEY = 'odysseia-theme';

export function useTheme() {
  const [currentTheme, setCurrentTheme] = useState<ThemeName>(() => {
    // 从 localStorage 读取保存的主题
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      return (saved as ThemeName) || 'dark';
    } catch {
      return 'dark';
    }
  });

  const theme: Theme = themes[currentTheme];

  // 切换主题
  const toggleTheme = () => {
    setCurrentTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // 设置指定主题
  const setTheme = (themeName: ThemeName) => {
    setCurrentTheme(themeName);
  };

  // 保存主题到 localStorage
  useEffect(() => {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, currentTheme);
    } catch {
      // 忽略存储错误
    }
  }, [currentTheme]);

  return {
    theme,
    currentTheme,
    toggleTheme,
    setTheme,
  };
}
