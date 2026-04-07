import type { SearchToken } from '@/shared/lib/searchTokenizer';
import { User, X } from 'lucide-react';

import type { SortMethod, TagLogic } from '@/features/search/hooks/useSearchParams';

interface SearchFilterPanelProps {
  availableTags: string[];
  excludeAuthorDraft: string;
  excludeAuthorTokens: SearchToken[];
  hasPanelFilters: boolean;
  includeAuthorDraft: string;
  includeAuthorTokens: SearchToken[];
  mergedExcludeTags: string[];
  mergedIncludeTags: string[];
  onClearFilters: () => void;
  onExcludeAuthorDraftChange: (value: string) => void;
  onIncludeAuthorDraftChange: (value: string) => void;
  onPreferenceTagSyncToggle: () => void;
  onRemoveAuthorToken: (token: SearchToken) => void;
  onSortMethodChange: (value: SortMethod) => void;
  onSubmitAuthorDraft: (mode: 'include' | 'exclude') => void;
  onTagLogicChange: (value: TagLogic) => void;
  onTimeFromChange: (value: string) => void;
  onTimeToChange: (value: string) => void;
  onToggleTagToken: (tagName: string, mode: 'include' | 'exclude') => void;
  preferenceExcludeTags: string[];
  preferenceIncludeTags: string[];
  sortMethod: SortMethod;
  syncPreferenceTags: boolean;
  tagLogic: TagLogic;
  timeFrom: string;
  timeTo: string;
}

export function SearchFilterPanel({
  availableTags,
  excludeAuthorDraft,
  excludeAuthorTokens,
  hasPanelFilters,
  includeAuthorDraft,
  includeAuthorTokens,
  mergedExcludeTags,
  mergedIncludeTags,
  onClearFilters,
  onExcludeAuthorDraftChange,
  onIncludeAuthorDraftChange,
  onPreferenceTagSyncToggle,
  onRemoveAuthorToken,
  onSortMethodChange,
  onSubmitAuthorDraft,
  onTagLogicChange,
  onTimeFromChange,
  onTimeToChange,
  onToggleTagToken,
  preferenceExcludeTags,
  preferenceIncludeTags,
  sortMethod,
  syncPreferenceTags,
  tagLogic,
  timeFrom,
  timeTo,
}: SearchFilterPanelProps) {
  const hasPreferenceTags = preferenceIncludeTags.length + preferenceExcludeTags.length > 0;

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--od-text-primary)]">高级筛选</h3>
        {hasPanelFilters && (
          <button
            onClick={onClearFilters}
            className="text-xs text-[var(--od-accent)] hover:underline"
          >
            清空筛选
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="topbar-sort" className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-[var(--od-text-tertiary)]">
            排序方式
          </label>
          <select
            id="topbar-sort"
            value={sortMethod}
            onChange={(e) => onSortMethodChange(e.target.value as SortMethod)}
            className="od-chrome-surface w-full rounded-xl border border-white/[0.06] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
          >
            <option value="last_active_desc">最近活跃</option>
            <option value="created_desc">最新发布</option>
            <option value="reply_desc">回复数</option>
            <option value="reaction_desc">反应数</option>
            <option value="relevance">相关度</option>
          </select>
        </div>

        <div>
          <label htmlFor="topbar-tagLogic" className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-[var(--od-text-tertiary)]">
            标签逻辑
          </label>
          <select
            id="topbar-tagLogic"
            value={tagLogic}
            onChange={(e) => onTagLogicChange(e.target.value as TagLogic)}
            className="od-chrome-surface w-full rounded-xl border border-white/[0.06] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
          >
            <option value="and">全部包含 (AND)</option>
            <option value="or">任一即可 (OR)</option>
          </select>
        </div>

        <div>
          <label htmlFor="topbar-timeFrom" className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-[var(--od-text-tertiary)]">
            不早于
          </label>
          <input
            id="topbar-timeFrom"
            type="date"
            value={timeFrom}
            onChange={(e) => onTimeFromChange(e.target.value)}
            className="od-chrome-surface w-full rounded-xl border border-white/[0.06] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
          />
        </div>

        <div>
          <label htmlFor="topbar-timeTo" className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-[var(--od-text-tertiary)]">
            不晚于
          </label>
          <input
            id="topbar-timeTo"
            type="date"
            value={timeTo}
            onChange={(e) => onTimeToChange(e.target.value)}
            className="od-chrome-surface w-full rounded-xl border border-white/[0.06] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
          />
        </div>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
              标签筛选
            </h4>
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-[var(--od-text-tertiary)] text-right">
                点击标签切换包含 / 排除 / 取消，不在这里显示删除按钮
              </span>
              <div className={`flex shrink-0 items-center gap-2 rounded-full border px-2.5 py-1.5 ${
                hasPreferenceTags
                  ? 'border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)]'
                  : 'border-[color-mix(in_srgb,var(--od-text-secondary)_10%,transparent)] bg-[color-mix(in_srgb,var(--od-surface-input)_42%,transparent)] opacity-60'
              }`}>
                <span className="text-[11px] font-semibold text-[var(--od-text-secondary)]">同步偏好标签</span>
                <button
                  type="button"
                  onClick={onPreferenceTagSyncToggle}
                  data-checked={syncPreferenceTags}
                  disabled={!hasPreferenceTags}
                  className="od-toggle scale-[0.88] disabled:cursor-not-allowed disabled:opacity-50"
                  title={hasPreferenceTags ? '同步偏好标签' : '先在偏好页设置标签'}
                >
                  <div className="od-toggle-thumb" />
                </button>
              </div>
            </div>
          </div>
          <div className="mb-3 flex flex-wrap items-center gap-2 text-[11px] text-[var(--od-text-tertiary)]">
            <span>发现偏好标签</span>
            {hasPreferenceTags ? (
              <>
                {preferenceIncludeTags.map((tag) => (
                  <span key={`pref-include-${tag}`} className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-emerald-300">+ {tag}</span>
                ))}
                {preferenceExcludeTags.map((tag) => (
                  <span key={`pref-exclude-${tag}`} className="rounded-full bg-rose-500/10 px-2.5 py-1 text-rose-300">- {tag}</span>
                ))}
              </>
            ) : (
              <span>当前还没有保存偏好标签</span>
            )}
          </div>
          <div className="od-chrome-surface flex max-h-[180px] flex-wrap gap-2 overflow-y-auto rounded-2xl p-3">
            {availableTags.length > 0 ? (
              availableTags.map((tag) => {
                const isIncluded = mergedIncludeTags.includes(tag);
                const isExcluded = mergedExcludeTags.includes(tag);

                return (
                  <div key={tag} className="od-content-surface flex items-center rounded-full p-1">
                    <button
                      type="button"
                      onClick={() => {
                        if (isIncluded) {
                          onToggleTagToken(tag, 'exclude');
                          return;
                        }
                        if (isExcluded) {
                          onToggleTagToken(tag, 'exclude');
                          return;
                        }
                        onToggleTagToken(tag, 'include');
                      }}
                      className={`rounded-full px-3 py-1 text-xs transition-colors ${
                        isIncluded
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : isExcluded
                            ? 'bg-rose-500/20 text-rose-300'
                            : 'text-[var(--od-text-secondary)] hover:bg-emerald-500/10 hover:text-emerald-300'
                      }`}
                    >
                      {isIncluded ? '✓ ' : isExcluded ? '✕ ' : ''}{tag}
                    </button>
                  </div>
                );
              })
            ) : (
              <span className="text-sm text-[var(--od-text-tertiary)]">当前上下文暂时没有可用标签</span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
              <User className="h-3.5 w-3.5" />
              包含作者
            </label>
            <div className="flex gap-2">
              <input
                value={includeAuthorDraft}
                onChange={(e) => onIncludeAuthorDraftChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onSubmitAuthorDraft('include');
                  }
                }}
                placeholder="输入昵称或用户名"
                className="od-chrome-surface w-full rounded-xl border border-white/[0.06] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
              />
              <button
                type="button"
                onClick={() => onSubmitAuthorDraft('include')}
                className="rounded-xl bg-emerald-500/20 px-3 text-sm text-emerald-300 transition-colors hover:bg-emerald-500/30"
              >
                添加
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {includeAuthorTokens.map((token) => (
                <button
                  key={`${token.mode}-${token.value}`}
                  type="button"
                  onClick={() => onRemoveAuthorToken(token)}
                  className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-3 py-1 text-xs text-emerald-300"
                >
                  {token.value}
                  <X className="h-3 w-3" />
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
              <User className="h-3.5 w-3.5" />
              排除作者
            </label>
            <div className="flex gap-2">
              <input
                value={excludeAuthorDraft}
                onChange={(e) => onExcludeAuthorDraftChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onSubmitAuthorDraft('exclude');
                  }
                }}
                placeholder="输入昵称或用户名"
                className="od-chrome-surface w-full rounded-xl border border-white/[0.06] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
              />
              <button
                type="button"
                onClick={() => onSubmitAuthorDraft('exclude')}
                className="rounded-xl bg-rose-500/20 px-3 text-sm text-rose-300 transition-colors hover:bg-rose-500/30"
              >
                添加
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {excludeAuthorTokens.map((token) => (
                <button
                  key={`${token.mode}-${token.value}`}
                  type="button"
                  onClick={() => onRemoveAuthorToken(token)}
                  className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-3 py-1 text-xs text-rose-300"
                >
                  {token.value}
                  <X className="h-3 w-3" />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
