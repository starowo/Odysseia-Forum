
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

export function ThemeToggle() {
  const { currentTheme, toggleTheme } = useTheme();

  const isDarkTheme =
    currentTheme === 'discordDark' || currentTheme === 'tweakGrayDark';

  const handleClick = () => {
    // 仅切换主题，具体亮暗过渡交给全局的 od-theme-transition 控制
    toggleTheme();
  };

  return (
    <button
      onClick={handleClick}
      className="relative inline-flex h-7 w-12 items-center rounded-full border border-[var(--od-border)] bg-[var(--od-bg-tertiary)] px-1 text-[var(--od-text-secondary)] shadow-sm transition-all duration-500 hover:border-[var(--od-accent)] hover:bg-[var(--od-card)]"
      aria-label="切换主题"
      title={isDarkTheme ? '切换到浅色模式' : '切换到深色模式'}
    >
      {/* 轨道背景渐变，左侧偏亮，右侧偏暗 */}
      <span className="pointer-events-none absolute inset-0 rounded-full bg-[radial-gradient(circle_at_20%_50%,rgba(255,255,255,0.12)_0,transparent_55%),radial-gradient(circle_at_80%_50%,rgba(0,0,0,0.4)_0,transparent_55%)]" />
      {/* 滑块 */}
      <span
        className={`relative z-10 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--od-card)] text-[var(--od-text-primary)] shadow transition-transform duration-500 ${isDarkTheme ? 'translate-x-0' : 'translate-x-5'
          }`}
      >
        {isDarkTheme ? (
          <Moon className="h-3.5 w-3.5" />
        ) : (
          <Sun className="h-3.5 w-3.5" />
        )}
      </span>
    </button>
  );
}
