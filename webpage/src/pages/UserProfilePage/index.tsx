import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FileText, Heart, MessageCircle, RefreshCw } from 'lucide-react';

import { searchApi } from '@/features/search/api/searchApi';
import { useSettings } from '@/shared/hooks/useSettings';
import { ThreadCard } from '@/entities/thread/ThreadCard';
import { ThreadListItem } from '@/entities/thread/ThreadListItem';
import type { Thread } from '@/entities/thread/types';
import { UserStatsGrid } from '@/entities/user/UserStatsGrid';
import { ThreadPreviewOverlay } from '@/widgets/thread-preview/ThreadPreviewOverlay';

export function UserProfilePage() {
  const { userId } = useParams();
  const { settings } = useSettings();
  const [previewThread, setPreviewThread] = useState<Thread | null>(null);

  const threadsQuery = useQuery({
    queryKey: ['user-profile', userId, 'threads'],
    enabled: Boolean(userId),
    queryFn: () =>
      searchApi.search({
        include_authors: userId ? [userId] : [],
        author_name: userId || undefined,
        sort_method: 'created_desc',
        limit: 48,
      }),
    staleTime: 60 * 1000,
  });

  const threads = useMemo(() => ((threadsQuery.data?.results || []) as Thread[]), [threadsQuery.data?.results]);
  const author = threads[0]?.author;
  const authorName =
    author?.display_name || author?.global_name || author?.name || (userId ? `作者 ${userId}` : '未知作者');

  const totalReactions = threads.reduce((sum, item) => sum + (Number(item.reaction_count) || 0), 0);
  const totalReplies = threads.reduce((sum, item) => sum + (Number(item.reply_count) || 0), 0);

  const stats = [
    { label: '帖子数量', value: threadsQuery.data?.total || 0 },
    { label: '累计点赞', value: totalReactions },
    { label: '累计回复', value: totalReplies },
    { label: '当前加载', value: threads.length },
  ];

  return (
    <>
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
        <div className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 overflow-hidden rounded-full bg-[var(--od-bg-tertiary)]">
                <img
                  src={author?.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'}
                  alt={authorName}
                  className="h-full w-full object-cover"
                />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">{authorName}</h1>
                <p className="text-sm text-[var(--od-text-secondary)]">作者主页（轻量版）</p>
                {author?.id && <p className="text-xs text-[var(--od-text-tertiary)]">ID: {author.id}</p>}
              </div>
            </div>

            <button
              type="button"
              onClick={() => void threadsQuery.refetch()}
              className="inline-flex items-center gap-1 rounded-md border border-[var(--od-border)] px-2.5 py-1 text-xs text-[var(--od-text-secondary)]"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              刷新
            </button>
          </div>
        </div>

        <UserStatsGrid items={stats} />

        <section className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 sm:p-5">
          <div className="mb-4 flex items-center gap-2 text-sm text-[var(--od-text-secondary)]">
            <FileText className="h-4 w-4 text-[var(--od-accent)]" />
            <span>作者帖子列表</span>
            <span className="mx-1 text-[var(--od-text-tertiary)]">·</span>
            <Heart className="h-4 w-4" />
            <span>{totalReactions}</span>
            <span className="mx-1 text-[var(--od-text-tertiary)]">·</span>
            <MessageCircle className="h-4 w-4" />
            <span>{totalReplies}</span>
          </div>

          {threadsQuery.isLoading ? (
            <p className="text-sm text-[var(--od-text-secondary)]">加载作者帖子中...</p>
          ) : threadsQuery.isError ? (
            <p className="text-sm text-[var(--od-error)]">加载失败，请稍后重试。</p>
          ) : threads.length === 0 ? (
            <p className="text-sm text-[var(--od-text-secondary)]">暂无可展示帖子。</p>
          ) : (
            <div
              className={
                settings.layoutMode === 'list'
                  ? 'flex flex-col space-y-od-list-gap'
                  : 'grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
              }
            >
              {threads.map((thread) =>
                settings.layoutMode === 'list' ? (
                  <ThreadListItem key={thread.thread_id} thread={thread} onPreview={setPreviewThread} />
                ) : (
                  <ThreadCard key={thread.thread_id} thread={thread} onPreview={setPreviewThread} />
                ),
              )}
            </div>
          )}
        </section>
      </div>

      {previewThread && (
        <ThreadPreviewOverlay thread={previewThread} onClose={() => setPreviewThread(null)} />
      )}
    </>
  );
}
