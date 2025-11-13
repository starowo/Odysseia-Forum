import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

export function ThemeToggle() {
  const { currentTheme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="rounded-md p-2 text-[#b5bac1] transition-all duration-200 hover:bg-[#4e5058] hover:text-[#f2f3f5]"
      aria-label="切换主题"
      title={currentTheme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
    >
      {currentTheme === 'dark' ? (
        <Sun className="h-5 w-5" />
      ) : (
        <Moon className="h-5 w-5" />
      )}
    </button>
  );
}
