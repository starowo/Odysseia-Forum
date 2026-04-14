import { BookOpen, RefreshCw } from 'lucide-react';

import { BooklistCard } from '@/entities/booklist/BooklistCard';
import type { Booklist } from '@/entities/booklist/types';
import { FluidDivider } from '@/shared/ui/FluidDivider';

export type BooklistSubTab = 'mine' | 'collected';

interface MeBooklistsSectionProps {
  activeBooklists: Booklist[];
  collectLoading: boolean;
  isLoading: boolean;
  subTab: BooklistSubTab;
  userId?: string | number | null;
  onCreate: () => void;
  onDelete: (item: Booklist) => void;
  onEdit: (item: Booklist) => void;
  onOpen: (id: number) => void;
  onRefresh: () => void;
  onSetSubTab: (tab: BooklistSubTab) => void;
  onToggleCollect: (item: Booklist) => void;
}

export function MeBooklistsSection({
  activeBooklists,
  collectLoading,
  isLoading,
  subTab,
  userId,
  onCreate,
  onDelete,
  onEdit,
  onOpen,
  onRefresh,
  onSetSubTab,
  onToggleCollect,
}: MeBooklistsSectionProps) {
  return (
    <section className="px-1">
      <FluidDivider label="Booklists" className="mb-8" />
      <div className="mb-6 flex flex-col items-center gap-3 text-center">
        <div className="flex items-center gap-2 justify-center">
          <BookOpen className="h-4 w-4 text-[var(--od-accent)]" />
          <h2 className="od-text-title">我的书单</h2>
        </div>
        <button
          type="button"
          onClick={onCreate}
          className="od-inline-action od-inline-action-primary w-full justify-center sm:w-auto"
        >
          新建书单
        </button>
      </div>

      <div className="mb-6 flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          onClick={() => onSetSubTab('mine')}
          className={`od-pill-chip text-xs ${
            subTab === 'mine'
              ? 'bg-[var(--od-accent)] text-white font-od-bold'
              : 'text-[var(--od-text-secondary)] font-od-medium'
          }`}
        >
          我的创建
        </button>
        <button
          type="button"
          onClick={() => onSetSubTab('collected')}
          className={`od-pill-chip text-xs ${
            subTab === 'collected'
              ? 'bg-[var(--od-accent)] text-white font-od-bold'
              : 'text-[var(--od-text-secondary)] font-od-medium'
          }`}
        >
          我的收藏
        </button>
        <button
          type="button"
          onClick={onRefresh}
          className="od-inline-action od-inline-action-ghost"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </button>
      </div>

      {isLoading ? (
        <p className="od-text-body">正在加载书单...</p>
      ) : activeBooklists.length === 0 ? (
        <p className="od-text-body">这个分组里还没有内容，去创建一个吧～</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {activeBooklists.map((booklist) => (
            <BooklistCard
              key={booklist.id}
              booklist={booklist}
              canManage={String(booklist.owner_id) === String(userId)}
              onOpen={onOpen}
              onToggleCollect={onToggleCollect}
              onEdit={onEdit}
              onDelete={onDelete}
              collectLoading={collectLoading}
            />
          ))}
        </div>
      )}
    </section>
  );
}
