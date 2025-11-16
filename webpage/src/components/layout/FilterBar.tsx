interface FilterBarProps {
  timeFrom: string;
  timeTo: string;
  sortMethod: string;
  tagLogic: 'and' | 'or';
  onTimeFromChange: (value: string) => void;
  onTimeToChange: (value: string) => void;
  onSortMethodChange: (value: string) => void;
  onTagLogicChange: (value: 'and' | 'or') => void;
}

export function FilterBar({
  timeFrom,
  timeTo,
  sortMethod,
  tagLogic,
  onTimeFromChange,
  onTimeToChange,
  onSortMethodChange,
  onTagLogicChange,
}: FilterBarProps) {
  return (
    <div className="mb-4 rounded-xl bg-[var(--od-card)] p-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
        {/* 发帖不早于 */}
        <div>
          <label
            htmlFor="timeFrom"
            className="mb-1.5 block text-xs font-medium text-[var(--od-text-secondary)]"
          >
            发帖不早于
          </label>
          <input
            id="timeFrom"
            type="date"
            value={timeFrom}
            onChange={(e) => onTimeFromChange(e.target.value)}
            className="w-full rounded-md bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]"
          />
        </div>

        {/* 发帖不晚于 */}
        <div>
          <label
            htmlFor="timeTo"
            className="mb-1.5 block text-xs font-medium text-[var(--od-text-secondary)]"
          >
            发帖不晚于
          </label>
          <input
            id="timeTo"
            type="date"
            value={timeTo}
            onChange={(e) => onTimeToChange(e.target.value)}
            className="w-full rounded-md bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]"
          />
        </div>

        {/* 排序方式 */}
        <div>
          <label
            htmlFor="sortMethod"
            className="mb-1.5 block text-xs font-medium text-[var(--od-text-secondary)]"
          >
            排序方式
          </label>
          <select
            id="sortMethod"
            value={sortMethod}
            onChange={(e) => onSortMethodChange(e.target.value)}
            className="w-full rounded-md bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]"
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
          <label
            htmlFor="tagLogic"
            className="mb-1.5 block text-xs font-medium text-[var(--od-text-secondary)]"
          >
            标签逻辑
          </label>
          <select
            id="tagLogic"
            value={tagLogic}
            onChange={(e) => onTagLogicChange(e.target.value as 'and' | 'or')}
            className="w-full rounded-md bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]"
          >
            <option value="and">全部包含 (AND)</option>
            <option value="or">任一即可 (OR)</option>
          </select>
        </div>
      </div>
    </div>
  );
}
