import { ReactNode, useEffect } from 'react';
import { useTheme } from '@/hooks/useTheme';

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const { theme, currentTheme } = useTheme();

  useEffect(() => {
    if (typeof document === 'undefined') return;

    const root = document.documentElement;
    const colors = theme.colors;

    // 开启全局主题平滑过渡（几秒钟缓慢从亮到暗/从暗到亮）
    root.classList.add('od-theme-transition');

    const timeoutId = window.setTimeout(() => {
      root.classList.remove('od-theme-transition');
    }, 1800); // 1.8s 过渡时长，避免“一瞬间闪眼睛”

    root.style.setProperty('--od-bg', colors.background);
    root.style.setProperty('--od-bg-secondary', colors.backgroundSecondary);
    root.style.setProperty('--od-bg-tertiary', colors.backgroundTertiary);
    root.style.setProperty('--od-card', colors.card);
    root.style.setProperty('--od-card-hover', colors.cardHover);
    root.style.setProperty('--od-text-primary', colors.textPrimary);
    root.style.setProperty('--od-text-secondary', colors.textSecondary);
    root.style.setProperty('--od-text-tertiary', colors.textTertiary);
    root.style.setProperty('--od-accent', colors.accent);
    root.style.setProperty('--od-accent-hover', colors.accentHover);
    root.style.setProperty('--od-link', colors.link);
    root.style.setProperty('--od-link-hover', colors.linkHover);
    root.style.setProperty('--od-border', colors.border);
    root.style.setProperty('--od-border-strong', colors.borderStrong);
    root.style.setProperty('--od-success', colors.success);
    root.style.setProperty('--od-warning', colors.warning);
    root.style.setProperty('--od-error', colors.error);
    root.style.setProperty('--od-info', colors.info);

    // 方便调试：在 html 标签上标记当前主题
    root.setAttribute('data-od-theme', currentTheme);

    return () => {
      root.classList.remove('od-theme-transition');
      window.clearTimeout(timeoutId);
    };
  }, [theme, currentTheme]);

  return <>{children}</>;
}