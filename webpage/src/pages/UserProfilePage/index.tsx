import { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FileText, Heart, MessageCircle, RefreshCw } from 'lucide-react';

import { searchApi } from '@/features/search/api/searchApi';
import { ThreadResultsCollection } from '@/entities/thread/ThreadResultsCollection';
import type { Thread } from '@/entities/thread/types';
import { UserHeaderCard } from '@/entities/user/UserHeaderCard';
import { UserStatsGrid } from '@/entities/user/UserStatsGrid';
import { usePreviewThread } from '@/features/search/hooks/usePreviewThread';
import { FluidDivider } from '@/shared/ui/FluidDivider';

export function UserProfilePage() {
  const { userId } = useParams();
  const { openPreview } = usePreviewThread();

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
    {
      label: '帖子数量',
      value: threadsQuery.data?.total || 0,
      icon: FileText,
    },
    {
      label: '累计点赞',
      value: totalReactions,
      icon: Heart,
    },
    {
      label: '累计回复',
      value: totalReplies,
      icon: MessageCircle,
    },
    {
      label: '当前加载',
      value: threads.length,
      icon: RefreshCw,
    },
  ];

  return (
    <>
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-10 p-4 sm:p-6 lg:gap-14 lg:p-8">
        <section>
          <FluidDivider label="Author" tone="strong" className="mb-8 lg:mb-10" />
          <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
            <div className="flex flex-col items-center gap-4">
              <UserHeaderCard
                user={{
                  id: author?.id || userId || 'unknown',
                  username: author?.name || authorName,
                  global_name: authorName,
                  avatar: undefined,
                }}
                avatarUrl={author?.avatar_url || null}
                subtitle={`作者主页 · ${author?.id ? `ID: ${author.id}` : '正在加载作者信息'}`}
              />

              <button
                type="button"
                onClick={() => void threadsQuery.refetch()}
                className="od-inline-action od-inline-action-ghost w-full justify-center sm:w-auto"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>
            </div>

            <div className="mx-auto h-px w-16 bg-[color-mix(in_srgb,var(--od-text-secondary)_12%,transparent)]" />
            <UserStatsGrid items={stats} />
          </div>
        </section>

        <section className="px-1">
          <FluidDivider label="Threads" className="mb-8" />
          <div className="mb-6 flex flex-wrap items-center gap-2 text-sm text-[var(--od-text-secondary)]">
            <FileText className="h-4 w-4 text-[var(--od-accent)]" />
            <span>这位作者的帖子</span>
            <span className="mx-1 text-[var(--od-text-tertiary)]">·</span>
            <Heart className="h-4 w-4" />
            <span>{totalReactions}</span>
            <span className="mx-1 text-[var(--od-text-tertiary)]">·</span>
            <MessageCircle className="h-4 w-4" />
            <span>{totalReplies}</span>
          </div>

          {threadsQuery.isLoading ? (
            <p className="text-sm text-[var(--od-text-secondary)]">正在加载这位作者的帖子...</p>
          ) : threadsQuery.isError ? (
            <p className="text-sm text-[var(--od-error)]">加载失败了，稍后再试试吧。</p>
          ) : threads.length === 0 ? (
            <p className="text-sm text-[var(--od-text-secondary)]">这位作者还没有发布过帖子。</p>
          ) : (
            <ThreadResultsCollection
              threads={threads}
              onPreview={openPreview}
            />
          )}
        </section>
      </div>
    </>
  );
}
