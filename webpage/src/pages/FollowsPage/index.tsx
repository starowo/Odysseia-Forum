import { ThreadCard } from '@/entities/thread/ThreadCard';
import { ThreadCardSkeleton } from '@/entities/thread/ThreadCardSkeleton';
import { ThreadListItem } from '@/entities/thread/ThreadListItem';
import { ThreadListItemSkeleton } from '@/entities/thread/ThreadListItemSkeleton';
import type { Thread } from '@/entities/thread/types';
import { followsApi } from '@/features/follows/api/followsApi';
import { useSettings } from '@/shared/hooks/useSettings';
import { ThreadPreviewOverlay } from '@/widgets/thread-preview/ThreadPreviewOverlay';
import { useQuery } from '@tanstack/react-query';
import { Bookmark } from 'lucide-react';
import { useState } from 'react';

export function FollowsPage() {
  const { settings } = useSettings();
  const [previewThread, setPreviewThread] = useState<Thread | null>(null);

  const { data: followsData, isLoading } = useQuery({
    queryKey: ['follows'],
    queryFn: followsApi.getFollows,
    staleTime: 60 * 1000,
    refetchInterval: 30 * 1000,
    refetchOnWindowFocus: true,
  });

  const allFollows = followsData?.results || [];
  const unreadCount = followsData?.unread_count || 0;
  const follows = allFollows;

  const handleClosePreview = () => {
    setPreviewThread(null);
  };

  return (
    <>
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
        <div className="flex flex-col gap-2 border-b border-[var(--od-border)] pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--od-accent)]/10 text-[var(--od-accent)] shadow-inner">
              <Bookmark className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">我的关注</h1>
              <p className="text-sm text-[var(--od-text-secondary)]">跟踪你最感兴趣的帖子动态</p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-sm">
            <div className="flex flex-col items-end">
              <span className="font-medium text-[var(--od-text-primary)]">{allFollows.length} 个项目</span>
              {unreadCount > 0 && (
                <span className="font-bold text-[var(--od-accent)]">{unreadCount} 个未读更新</span>
              )}
            </div>
          </div>
        </div>

        {isLoading ? (
          <div
            className={
              settings.layoutMode === 'list'
                ? 'flex flex-col space-y-od-list-gap'
                : 'grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
            }
          >
            {Array.from({ length: 8 }).map((_, i) =>
              settings.layoutMode === 'list' ? (
                <ThreadListItemSkeleton key={i} />
              ) : (
                <ThreadCardSkeleton key={i} />
              ),
            )}
          </div>
        ) : follows.length > 0 ? (
          <div
            className={
              settings.layoutMode === 'list'
                ? 'flex flex-col space-y-od-list-gap'
                : 'grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
            }
          >
            {follows.map((thread) =>
              settings.layoutMode === 'list' ? (
                <ThreadListItem key={thread.thread_id} thread={thread} onPreview={setPreviewThread} />
              ) : (
                <ThreadCard key={thread.thread_id} thread={thread} onPreview={setPreviewThread} />
              ),
            )}
          </div>
        ) : (
          <div className="flex min-h-[300px] items-center justify-center rounded-2xl bg-[var(--od-card)] p-12 text-center shadow-sm">
            <div>
              <Bookmark className="mx-auto mb-4 h-12 w-12 text-[var(--od-text-tertiary)] opacity-20" />
              <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">暂无关注内容</h3>
              <p className="text-[var(--od-text-secondary)]">在搜索页面点击帖子右上角的书签来关注它吧！</p>
            </div>
          </div>
        )}
      </div>

      {previewThread && (
        <ThreadPreviewOverlay thread={previewThread} onClose={handleClosePreview} />
      )}
    </>
  );
}
