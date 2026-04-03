import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Compass, Megaphone, Plus, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

import { ThreadCard } from '@/entities/thread/ThreadCard';
import { BooklistCard } from '@/entities/booklist/BooklistCard';
import type { Booklist } from '@/entities/booklist/types';
import { plazaApi, PLAZA_RAILS, type PlazaRailKey } from '@/features/plaza/api/plazaApi';
import { BannerApplicationModal } from '@/features/banner/components/BannerApplicationModal';
import { booklistsApi } from '@/features/booklists/api/booklistsApi';
import { usePreviewStore } from '@/features/search/store/previewStore';

const railSortMap: Record<PlazaRailKey, string> = {
  latest: 'created_desc',
  reaction_surge: 'reaction_desc',
  discussion_surge: 'reply_desc',
  editors_pick: 'relevance',
};

export function PlazaPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setPreviewThreadId, setPreviewThread } = usePreviewStore();

  const [showBannerApply, setShowBannerApply] = useState(false);

  const bannersQuery = useQuery({
    queryKey: ['plaza', 'banners'],
    queryFn: plazaApi.getBanners,
    staleTime: 60 * 1000,
  });

  const booklistsQuery = useQuery({
    queryKey: ['plaza', 'booklists'],
    queryFn: plazaApi.getFeaturedBooklists,
    staleTime: 2 * 60 * 1000,
  });

  const latestQuery = useQuery({
    queryKey: ['plaza', 'rail', 'latest'],
    queryFn: () => plazaApi.getRail('latest'),
    staleTime: 90 * 1000,
  });
  const reactionQuery = useQuery({
    queryKey: ['plaza', 'rail', 'reaction_surge'],
    queryFn: () => plazaApi.getRail('reaction_surge'),
    staleTime: 90 * 1000,
  });
  const discussionQuery = useQuery({
    queryKey: ['plaza', 'rail', 'discussion_surge'],
    queryFn: () => plazaApi.getRail('discussion_surge'),
    staleTime: 90 * 1000,
  });
  const pickQuery = useQuery({
    queryKey: ['plaza', 'rail', 'editors_pick'],
    queryFn: () => plazaApi.getRail('editors_pick'),
    staleTime: 90 * 1000,
  });

  const railResultMap = useMemo(
    () => ({
      latest: latestQuery.data || [],
      reaction_surge: reactionQuery.data || [],
      discussion_surge: discussionQuery.data || [],
      editors_pick: pickQuery.data || [],
    }),
    [latestQuery.data, reactionQuery.data, discussionQuery.data, pickQuery.data],
  );

  const collectMutation = useMutation({
    mutationFn: ({ id, collected }: { id: number; collected: boolean }) =>
      collected ? booklistsApi.uncollect([id]) : booklistsApi.collect([id]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plaza', 'booklists'] });
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
      queryClient.invalidateQueries({ queryKey: ['booklist-detail'] });
    },
    onError: () => toast.error('收藏状态更新失败'),
  });

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-8 p-4 sm:p-6 lg:p-8">
      <section className="overflow-hidden rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)]">
        <div className="flex flex-col gap-4 border-b border-[var(--od-border)] bg-[var(--od-bg-secondary)] p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--od-accent)]/12 text-[var(--od-accent)]">
              <Compass className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">内容广场</h1>
              <p className="mt-1 text-sm text-[var(--od-text-secondary)]">Banner 曝光、推荐卡流、书单精选在这里汇总</p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowBannerApply(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--od-accent-hover)]"
          >
            <Megaphone className="h-4 w-4" />
            申请 Banner
          </button>
        </div>

        {bannersQuery.isLoading ? (
          <div className="grid gap-4 p-5 md:grid-cols-2">
            {Array.from({ length: 2 }).map((_, idx) => (
              <div key={idx} className="h-44 animate-pulse rounded-xl bg-[var(--od-bg-tertiary)]" />
            ))}
          </div>
        ) : bannersQuery.data && bannersQuery.data.length > 0 ? (
          <div className="grid gap-4 p-5 md:grid-cols-2">
            {bannersQuery.data.slice(0, 4).map((banner) => (
              <button
                key={`${banner.thread_id}-${banner.cover_image_url}`}
                type="button"
                onClick={() => setPreviewThreadId(banner.thread_id)}
                className="group relative h-44 overflow-hidden rounded-xl border border-[var(--od-border)] text-left"
              >
                <img
                  src={banner.cover_image_url}
                  alt={banner.title}
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
                <div className="absolute bottom-0 left-0 right-0 p-3">
                  <p className="line-clamp-2 text-sm font-semibold text-white">{banner.title}</p>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="p-5 text-sm text-[var(--od-text-secondary)]">当前没有可展示的 Banner。</div>
        )}
      </section>

      <section className="space-y-6">
        {PLAZA_RAILS.map((rail) => {
          const list = railResultMap[rail.key];
          if (!list || list.length === 0) return null;

          return (
            <div key={rail.key} className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 sm:p-5">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-[var(--od-text-primary)]">{rail.title}</h2>
                  <p className="text-sm text-[var(--od-text-secondary)]">{rail.subtitle}</p>
                </div>
                <Link
                  to={`/?sort=${railSortMap[rail.key]}`}
                  className="rounded-md bg-[var(--od-bg-secondary)] px-3 py-1.5 text-xs font-semibold text-[var(--od-text-secondary)] transition-colors hover:text-[var(--od-text-primary)]"
                >
                  查看更多
                </Link>
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {list.map((thread) => (
                  <ThreadCard
                    key={`${rail.key}-${thread.thread_id}`}
                    thread={thread}
                    onPreview={(item) => setPreviewThread(item)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </section>

      <section className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 sm:p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-[var(--od-text-primary)]">书单精选</h2>
            <p className="text-sm text-[var(--od-text-secondary)]">按收藏热度筛选的优质合集</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate('/booklists')}
              className="rounded-md bg-[var(--od-bg-secondary)] px-3 py-1.5 text-xs font-semibold text-[var(--od-text-secondary)] transition-colors hover:text-[var(--od-text-primary)]"
            >
              全部书单
            </button>
            <button
              type="button"
              onClick={() => navigate('/booklists')}
              className="inline-flex items-center gap-1 rounded-md bg-[var(--od-accent)] px-3 py-1.5 text-xs font-semibold text-white"
            >
              <Plus className="h-3.5 w-3.5" />
              创建
            </button>
          </div>
        </div>

        {booklistsQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, idx) => (
              <div key={idx} className="h-72 animate-pulse rounded-xl bg-[var(--od-bg-tertiary)]" />
            ))}
          </div>
        ) : booklistsQuery.data && booklistsQuery.data.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {booklistsQuery.data.map((booklist: Booklist) => (
              <BooklistCard
                key={booklist.id}
                booklist={booklist}
                canManage={false}
                onOpen={(id) => navigate(`/booklists/${id}`)}
                onToggleCollect={(item) =>
                  collectMutation.mutate({ id: item.id, collected: Boolean(item.collected_flag) })
                }
                onEdit={() => undefined}
                onDelete={() => undefined}
                collectLoading={collectMutation.isPending}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-bg-secondary)] p-6 text-sm text-[var(--od-text-secondary)]">
            暂无可推荐书单。
          </div>
        )}
      </section>

      <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 text-xs text-[var(--od-text-tertiary)]">
        <div className="inline-flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[var(--od-accent)]" />
          推荐由综合排序 + 时间窗规则生成，后续将加入个性化权重。
        </div>
      </div>

      <BannerApplicationModal isOpen={showBannerApply} onClose={() => setShowBannerApply(false)} />
    </div>
  );
}
