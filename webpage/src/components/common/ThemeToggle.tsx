import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

export function ThemeToggle() {
  const { currentTheme, toggleTheme } = useTheme();

  const isDarkTheme =
    currentTheme === 'discordDark' || currentTheme === 'tweakGrayDark';

  return (
    <button
      onClick={toggleTheme}
      className="rounded-md p-2 text-[var(--od-text-secondary)] transition-all duration-200 hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]"
      aria-label="切换主题"
      title={isDarkTheme ? '切换到浅色模式' : '切换到深色模式'}
    >
      {isDarkTheme ? (
        <Sun className="h-5 w-5" />
      ) : (
        <Moon className="h-5 w-5" />
      )}
    </button>
  );
}
