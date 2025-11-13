import { Grid, List } from 'lucide-react';

interface StatsBarProps {
  totalCount: number;
  perPage: number;
  openMode: 'app' | 'web';
  layoutMode: 'grid' | 'list';
  onPerPageChange: (value: number) => void;
  onOpenModeChange: (value: 'app' | 'web') => void;
  onLayoutModeChange: (value: 'grid' | 'list') => void;
}

export function StatsBar({
  totalCount,
  perPage,
  openMode,
  layoutMode,
  onPerPageChange,
  onOpenModeChange,
  onLayoutModeChange,
}: StatsBarProps) {
  return (
    <div className="mb-4 flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
      {/* 结果统计 */}
      <div className="text-sm text-[#b5bac1]">
        共 <span className="font-semibold text-[#f2f3f5]">{totalCount}</span> 条结果
      </div>

      {/* 控制选项 */}
      <div className="flex flex-wrap items-center gap-3">
        {/* 布局切换 */}
        <div className="flex items-center gap-1 rounded-md bg-[#2b2d31] p-1">
          <button
            onClick={() => onLayoutModeChange('grid')}
            className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              layoutMode === 'grid'
                ? 'bg-[#5865f2] text-white'
                : 'text-[#b5bac1] hover:bg-[#35373c] hover:text-[#f2f3f5]'
            }`}
            title="网格布局"
          >
            <Grid className="h-3.5 w-3.5" />
            <span>网格</span>
          </button>
          <button
            onClick={() => onLayoutModeChange('list')}
            className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              layoutMode === 'list'
                ? 'bg-[#5865f2] text-white'
                : 'text-[#b5bac1] hover:bg-[#35373c] hover:text-[#f2f3f5]'
            }`}
            title="列表布局"
          >
            <List className="h-3.5 w-3.5" />
            <span>列表</span>
          </button>
        </div>

        {/* 每页显示数量 */}
        <div className="flex items-center gap-2">
          <label htmlFor="perPage" className="text-xs text-[#b5bac1]">
            每页
          </label>
          <select
            id="perPage"
            value={perPage}
            onChange={(e) => onPerPageChange(Number(e.target.value))}
            className="rounded-md bg-[#4e5058] px-2 py-1 text-sm text-[#dbdee1] focus:outline-none focus:ring-2 focus:ring-[#5865f2]"
          >
            <option value={12}>12</option>
            <option value={24}>24</option>
            <option value={48}>48</option>
          </select>
        </div>

        {/* 跳转方式 */}
        <div className="flex items-center gap-2">
          <label htmlFor="openMode" className="text-xs text-[#b5bac1]">
            跳转方式
          </label>
          <select
            id="openMode"
            value={openMode}
            onChange={(e) => onOpenModeChange(e.target.value as 'app' | 'web')}
            className="rounded-md bg-[#4e5058] px-2 py-1 text-sm text-[#dbdee1] focus:outline-none focus:ring-2 focus:ring-[#5865f2]"
          >
            <option value="app">App</option>
            <option value="web">网页</option>
          </select>
        </div>
      </div>
    </div>
  );
}
