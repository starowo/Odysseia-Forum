import { Menu, ChevronUp, X, Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { SearchSuggestions } from '@/components/SearchSuggestions';
import { SearchTokenInput } from '@/components/common/SearchTokenInput';
import { AnimatedIcon } from '@/components/ui/animation/AnimatedIcon';
import type { Channel } from '@/types/thread.types';

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
  // 高级搜索面板相关
  timeFrom?: string;
  timeTo?: string;
  sortMethod?: string;
  tagLogic?: 'and' | 'or';
  tagMode?: 'included' | 'excluded';
  availableTags?: string[];
  tagStates?: Map<string, 'included' | 'excluded'>;
  channels?: Channel[];
  onTimeFromChange?: (value: string) => void;
  onTimeToChange?: (value: string) => void;
  onSortMethodChange?: (value: string) => void;
  onTagLogicChange?: (value: 'and' | 'or') => void;
  onTagModeChange?: (value: 'included' | 'excluded') => void;
  onTagClick?: (tag: string) => void;
  onClearAllTags?: () => void;
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
  timeFrom = '',
  timeTo = '',
  sortMethod = 'relevance',
  tagLogic = 'and',
  tagMode = 'included',
  availableTags = [],
  tagStates = new Map(),
  channels = [],
  onTimeFromChange,
  onTimeToChange,
  onSortMethodChange,
  onTagLogicChange,
  onTagModeChange,
  onTagClick,
  onClearAllTags,
}: TopBarProps) {
  const debounceTimerRef = useRef<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [isSearchHovered, setIsSearchHovered] = useState(false);
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [isTagExpanded, setIsTagExpanded] = useState(false);
  const maxTagsToShow = 10;

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

  const hasTags = availableTags.length > 0;

  return (
    <header className="sticky top-0 z-20 bg-[var(--od-bg-secondary)] shadow-lg">
      <div className="flex items-center gap-3 p-3 lg:pl-0">
        {/* 移动端菜单按钮 */}
        <button
          onClick={onMenuClick}
          className="rounded p-2 text-[var(--od-text-secondary)] transition-all duration-200 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)] lg:hidden"
          aria-label="打开菜单"
        >
          <AnimatedIcon icon={Menu} className="h-5 w-5" animation="rotate" trigger="click" />
        </button>

        {/* 搜索框（带 Token 支持） */}
        <div className="relative flex-1 min-w-0">
          <SearchTokenInput
            value={searchValue}
            onChange={onSearchChange}
            onSearch={() => {
              onSearch();
              setShowHistory(false);
            }}
            onFocus={() => setShowHistory(true)}
            onBlur={() => {
              // 延迟关闭，给用户时间点击建议
              setTimeout(() => setShowHistory(false), 200);
            }}
            placeholder="搜索标题、作者或内容... 💡 试试 $tag:标签$ 或 $author:作者$"
          />

          {/* 搜索建议下拉框 */}
          <SearchSuggestions
            isOpen={showHistory}
            currentQuery={searchValue}
            availableTags={availableTags}
            channels={channels}
            onSelect={(suggestion) => {
              const newValue = searchValue + suggestion;
              onSelectHistory?.(newValue);
              onSearchChange(newValue);
              setShowHistory(false);
            }}
            onClose={() => setShowHistory(false)}
            inputRef={searchInputRef}
          />
        </div>

        {/* 搜索按钮 */}
        <button
          onClick={onSearch}
          onMouseEnter={() => setIsSearchHovered(true)}
          onMouseLeave={() => setIsSearchHovered(false)}
          className="flex items-center justify-center leading-none rounded-md bg-[var(--od-accent)] p-2 text-white transition-all duration-200 hover:scale-105 hover:bg-[var(--od-accent-hover)]"
          aria-label="搜索"
        >
          <AnimatedIcon icon={Search} className="h-5 w-5" animation="pulse" isHovered={isSearchHovered} />
        </button>
      </div>

      {/* 高级搜索按钮 - 简化样式 */}
      <div className="flex justify-center px-3 pb-2 pt-1">
        <button
          type="button"
          onClick={() => setIsAdvancedOpen((prev) => !prev)}
          className="inline-flex items-center gap-1.5 px-2 py-1 text-xs text-[var(--od-text-tertiary)] transition-colors duration-200 hover:text-[var(--od-text-primary)]"
        >
          <AnimatedIcon
            icon={ChevronUp}
            className={`h-3.5 w-3.5 transition-transform ${isAdvancedOpen ? '' : 'rotate-180'}`}
            animation="bounce"
            trigger="hover"
          />
          <span>高级搜索</span>
        </button>
      </div>

      {/* 高级搜索折叠面板 */}
      <div
        className={`bg-[var(--od-bg-secondary)] transition-[max-height,opacity] duration-300 overflow-hidden border-t border-[var(--od-border)] ${isAdvancedOpen ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
          }`}
      >
        <div className="px-3 pb-3 pt-2">
          {/* 快捷填充按钮 */}
          <div className="mb-3 flex items-center gap-2 overflow-x-auto text-xs text-[var(--od-text-tertiary)]">
            <span className="flex-shrink-0">💡 高级搜索：</span>
            <button
              onClick={() => onQuickSearch?.('$tag:$ ')}
              className="whitespace-nowrap rounded-md bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 transition-all duration-200 hover:scale-105 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-link)]"
              title="点击填充到搜索框"
            >
              $tag:标签$
            </button>
            <span className="flex-shrink-0">·</span>
            <button
              onClick={() => onQuickSearch?.('$author:$ ')}
              className="whitespace-nowrap rounded-md bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 transition-all duration-200 hover:scale-105 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-link)]"
              title="点击填充到搜索框"
            >
              $author:作者$
            </button>
            <span className="flex-shrink-0">·</span>
            <button
              onClick={() => onQuickSearch?.('"关键词"')}
              className="whitespace-nowrap rounded-md bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 transition-all duration-200 hover:scale-105 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-link)]"
              title="点击填充到搜索框"
            >
              "精确匹配"
            </button>
            <span className="flex-shrink-0">·</span>
            <button
              onClick={() => onQuickSearch?.('-排除词')}
              className="whitespace-nowrap rounded-md bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 transition-all duration-200 hover:scale-105 hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-link)]"
              title="点击填充到搜索框"
            >
              -排除
            </button>
          </div>

          {/* 筛选器 */}
          <div className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-2 lg:grid-cols-4">
            {/* 发帖不早于 */}
            <div>
              <label htmlFor="timeFrom" className="mb-1.5 block text-xs font-medium text-[var(--od-text-secondary)]">
                发帖不早于
              </label>
              <input
                id="timeFrom"
                type="date"
                value={timeFrom}
                onChange={(e) => onTimeFromChange?.(e.target.value)}
                className="w-full rounded-md border-none bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]"
              />
            </div>

            {/* 发帖不晚于 */}
            <div>
              <label htmlFor="timeTo" className="mb-1.5 block text-xs font-medium text-[var(--od-text-secondary)]">
                发帖不晚于
              </label>
              <input
                id="timeTo"
                type="date"
                value={timeTo}
                onChange={(e) => onTimeToChange?.(e.target.value)}
                className="w-full rounded-md border-none bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]"
              />
            </div>

            {/* 排序方式 */}
            <div>
              <label htmlFor="sortMethod" className="mb-1.5 block text-xs font-medium text-[var(--od-text-secondary)]">
                排序方式
              </label>
              <select
                id="sortMethod"
                value={sortMethod}
                onChange={(e) => onSortMethodChange?.(e.target.value)}
                className="w-full rounded-md border-none bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]"
              >
                <option value="relevance">相关度</option>
                <option value="last_active_desc">最近活跃 ↓</option>
                <option value="created_desc">最新发布 ↓</option>
                <option value="reply_desc">回复数 ↓</option>
                <option value="reaction_desc">反应数 ↓</option>
              </select>
            </div>

            {/* 标签逻辑 */}
            <div>
              <label htmlFor="tagLogic" className="mb-1.5 block text-xs font-medium text-[var(--od-text-secondary)]">
                标签逻辑
              </label>
              <select
                id="tagLogic"
                value={tagLogic}
                onChange={(e) => onTagLogicChange?.(e.target.value as 'and' | 'or')}
                className="w-full rounded-md border-none bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]"
              >
                <option value="and">全部包含 (AND)</option>
                <option value="or">任一即可 (OR)</option>
              </select>
            </div>
          </div>

          {/* 标签筛选区 */}
          {hasTags && (
            <div className="border-t border-[var(--od-border)] pt-3">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium text-[var(--od-text-secondary)]">
                    标签筛选 ({tagStates.size}/{availableTags.length})
                  </span>
                  {availableTags.length > maxTagsToShow && (
                    <button
                      type="button"
                      onClick={() => setIsTagExpanded(!isTagExpanded)}
                      className="text-xs text-[var(--od-link)] hover:underline"
                    >
                      {isTagExpanded ? '收起' : `展开全部 (${availableTags.length})`}
                    </button>
                  )}
                  {tagStates.size > 0 && (
                    <button
                      type="button"
                      onClick={onClearAllTags}
                      className="flex items-center gap-1 text-xs text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]"
                    >
                      <X className="h-3 w-3" />
                      清空
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {/* 反选模式开关 */}
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <div className="relative">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={tagMode === 'excluded'}
                        onChange={(e) => onTagModeChange?.(e.target.checked ? 'excluded' : 'included')}
                      />
                      <div className="w-9 h-5 bg-[var(--od-bg-tertiary)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-red-500"></div>
                    </div>
                    <span className={`text-xs font-medium ${tagMode === 'excluded' ? 'text-red-500' : 'text-[var(--od-text-secondary)]'}`}>
                      反选模式
                    </span>
                  </label>


                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {(isTagExpanded ? availableTags : availableTags.slice(0, maxTagsToShow)).map((tag) => {
                  const state = tagStates.get(tag);
                  return (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => onTagClick?.(tag)}
                      className={`rounded-full px-3 py-1.5 text-sm font-medium transition-all duration-200 hover:scale-105 ${state === 'included'
                        ? 'bg-[var(--od-accent)] text-white'
                        : state === 'excluded'
                          ? 'bg-red-600 text-white line-through'
                          : 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)] hover:bg-[var(--od-card-hover)]'
                        }`}
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {!hasTags && (
            <p className="border-t border-[var(--od-border)] pt-3 text-xs text-[var(--od-text-tertiary)]">
              当前搜索结果暂时没有可用标签。
            </p>
          )}
        </div>
      </div>
    </header>
  );
}
