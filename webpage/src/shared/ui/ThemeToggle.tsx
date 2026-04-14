import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/shared/hooks/useTheme';

export function ThemeToggle() {
  const { isDarkTheme, toggleTheme } = useTheme();

  const handleClick = () => {
    toggleTheme();
  };

  const nextLabel = isDarkTheme ? '切换到浅色模式' : '切换到深色模式';

  return (
    <button
      onClick={handleClick}
      className="group inline-flex items-center gap-1.5 text-[var(--od-text-tertiary)] transition-colors duration-200 hover:text-[var(--od-text-primary)]"
      aria-label={nextLabel}
      title={nextLabel}
    >
      <span className="relative inline-flex h-5 w-5 items-center justify-center">
        <Sun
          className={`absolute h-4 w-4 transition-all duration-250 ${
            isDarkTheme
              ? 'scale-75 opacity-0 text-[var(--od-text-tertiary)]'
              : 'scale-100 opacity-100 text-[var(--od-accent)]'
          }`}
        />
        <Moon
          className={`absolute h-4 w-4 transition-all duration-250 ${
            isDarkTheme
              ? 'scale-100 opacity-100 text-[var(--od-accent)]'
              : 'scale-75 opacity-0 text-[var(--od-text-tertiary)]'
          }`}
        />
      </span>
      <span className="hidden text-[11px] font-medium uppercase tracking-[0.16em] text-current md:inline">
        {isDarkTheme ? 'Night' : 'Day'}
      </span>
    </button>
  );
}
