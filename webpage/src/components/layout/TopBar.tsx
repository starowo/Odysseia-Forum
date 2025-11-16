import { Search, Menu, Lightbulb } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { SearchHistoryDropdown } from '@/components/SearchHistory';

interface TopBarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearch: () => void;
  onMenuClick: () => void;
  enableAutoSearch?: boolean;
  autoSearchDelay?: number;
  onQuickSearch?: (template: string) => void;
  searchInputRef?: React.RefObject<HTMLInputElement>;
  onSelectHistory?: (query: string) => void;
}

export function TopBar({ 
  searchValue, 
  onSearchChange, 
  onSearch, 
  onMenuClick,
  enableAutoSearch = true,
  autoSearchDelay = 250,
  onQuickSearch,
  searchInputRef,
  onSelectHistory,
}: TopBarProps) {
  const debounceTimerRef = useRef<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  // 防抖自动搜索
  useEffect(() => {
    if (!enableAutoSearch) return;

    // 清除之前的定时器
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // 设置新的定时器
    debounceTimerRef.current = window.setTimeout(() => {
      onSearch();
    }, autoSearchDelay);

    // 清理函数
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchValue, enableAutoSearch, autoSearchDelay, onSearch]);

  return (
    <header className="sticky top-0 z-20 bg-[var(--od-bg-secondary)] shadow-lg">
      <div className="flex items-center gap-3 p-3">
        {/* 移动端菜单按钮 */}
        <button
          onClick={onMenuClick}
          className="rounded p-2 text-[var(--od-text-secondary)] transition-all duration-200 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)] lg:hidden"
          aria-label="打开菜单"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* 搜索框 */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--od-text-tertiary)]" />
          <input
            ref={searchInputRef}
            type="search"
            value={searchValue}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onSearch()}
            onFocus={() => setShowHistory(true)}
            placeholder="搜索标题、作者或内容..."
            className="w-full rounded-lg border-none bg-[var(--od-bg-secondary)] py-2 pl-9 pr-3 text-sm text-[var(--od-text-primary)] placeholder:text-[var(--od-text-tertiary)] focus:bg-[var(--od-bg-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]/60"
          />
          
          {/* 搜索历史下拉框 */}
          <SearchHistoryDropdown
            isOpen={showHistory}
            onSelectHistory={(query) => {
              onSelectHistory?.(query);
              setShowHistory(false);
            }}
            onClose={() => setShowHistory(false)}
            inputRef={searchInputRef}
          />
        </div>

        {/* 搜索按钮（移动端隐藏） */}
        <button
          onClick={onSearch}
          className="hidden rounded-md bg-[var(--od-accent)] px-4 py-1.5 text-sm font-medium text-white transition-all duration-200 hover:scale-105 hover:bg-[var(--od-accent-hover)] md:block"
        >
          搜索
        </button>
      </div>

      {/* 搜索提示 - 可点击快捷填充（与搜索框融为一体的纯色区域） */}
      <div className="bg-[var(--od-bg-secondary)] px-3 pb-3 pt-1">
        <div className="flex items-center gap-2 text-xs text-[var(--od-text-tertiary)]">
          <Lightbulb className="h-3.5 w-3.5 flex-shrink-0 text-[#f0b232]" />
          <span className="flex-shrink-0">高级搜索：</span>
          <button
            onClick={() => onQuickSearch?.('author:')}
            className="rounded-md bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 transition-all duration-200 hover:scale-105 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-link)]"
            title="点击填充到搜索框"
          >
            author:作者
          </button>
          <span className="flex-shrink-0">·</span>
          <button
            onClick={() => onQuickSearch?.('"关键词"')}
            className="rounded-md bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 transition-all duration-200 hover:scale-105 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-link)]"
            title="点击填充到搜索框"
          >
            "精确匹配"
          </button>
          <span className="flex-shrink-0">·</span>
          <button
            onClick={() => onQuickSearch?.('-排除词')}
            className="rounded-md bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 transition-all duration-200 hover:scale-105 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-link)]"
            title="点击填充到搜索框"
          >
            -排除
          </button>
        </div>
      </div>
    </header>
  );
}
