import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Compass, Dices, Plus, Sparkles } from 'lucide-react';

import { ThreadCard } from '@/entities/thread/ThreadCard';
import { BooklistCard } from '@/entities/booklist/BooklistCard';
import { BannerCarousel } from '@/widgets/layout/BannerCarousel';
import type { Booklist } from '@/entities/booklist/types';
import { plazaApi, PLAZA_RAILS, type PlazaRailKey } from '@/features/plaza/api/plazaApi';
import { useToggleBooklistCollection } from '@/features/booklists/hooks/useBooklistsData';
import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
import { resolveDiscoveryPreferencePatch } from '@/features/preferences/lib/discoveryPreferences';
import { plazaKeys } from '@/features/plaza/lib/queryKeys';
import { usePreviewStore } from '@/features/search/store/previewStore';
import { GUILD_ID } from '@/shared/config/channelCategories.private';
import { FluidDivider } from '@/shared/ui/FluidDivider';
import { useCardGridClass } from '@/shared/hooks/useSettings';

const railSortMap: Record<PlazaRailKey, string> = {
  latest: 'created_desc',
  reaction_surge: 'reaction_desc',
  discussion_surge: 'reply_desc',
  editors_pick: 'relevance',
};

export function PlazaPage() {
  const navigate = useNavigate();
  const setPreviewThread = usePreviewStore((state) => state.setPreviewThread);
  const { preferences } = useUserPreferences({ guildId: GUILD_ID });

  const [ignorePreferenceFilter, setIgnorePreferenceFilter] = useState(false);

  const plazaPreferencePatch = useMemo(
    () => (ignorePreferenceFilter
      ? null
      : resolveDiscoveryPreferencePatch({
        preferences,
        mode: 'plaza',
      })),
    [ignorePreferenceFilter, preferences],
  );

  const gridClass = useCardGridClass();

  const bannersQuery = useQuery({
    queryKey: plazaKeys.banners(),
    queryFn: plazaApi.getBanners,
    staleTime: 60 * 1000,
  });

  const booklistsQuery = useQuery({
    queryKey: plazaKeys.booklists(),
    queryFn: plazaApi.getFeaturedBooklists,
    staleTime: 2 * 60 * 1000,
  });

  const latestQuery = useQuery({
    queryKey: plazaKeys.rail('latest', plazaPreferencePatch || null),
    queryFn: () => plazaApi.getRail('latest', plazaPreferencePatch || undefined),
    staleTime: 90 * 1000,
  });
  const reactionQuery = useQuery({
    queryKey: plazaKeys.rail('reaction_surge', plazaPreferencePatch || null),
    queryFn: () => plazaApi.getRail('reaction_surge', plazaPreferencePatch || undefined),
    staleTime: 90 * 1000,
  });
  const discussionQuery = useQuery({
    queryKey: plazaKeys.rail('discussion_surge', plazaPreferencePatch || null),
    queryFn: () => plazaApi.getRail('discussion_surge', plazaPreferencePatch || undefined),
    staleTime: 90 * 1000,
  });
  const pickQuery = useQuery({
    queryKey: plazaKeys.rail('editors_pick', plazaPreferencePatch || null),
    queryFn: () => plazaApi.getRail('editors_pick', plazaPreferencePatch || undefined),
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

  const collectMutation = useToggleBooklistCollection();

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-10 p-4 sm:p-6 lg:p-8">
      <section className="relative min-h-[22rem]">
        <div className="relative z-10 flex flex-col justify-between pt-6 sm:pt-8 lg:pt-10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between mb-8">
            <div className="max-w-3xl">
              <div className="od-editorial-kicker mb-3 text-[var(--od-text-tertiary)]">
                <Compass className="h-3.5 w-3.5" />
                Plaza Spotlight
              </div>
              <h1 className="od-hero-title max-w-2xl text-[var(--od-text-primary)]">内容广场</h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)] sm:text-base sm:leading-7">
                我把今天广场里比较热闹、比较值得先看一眼的内容都理到这边啦。你不用急着挑，顺着往下逛就好，说不定一下子就碰到喜欢的。
              </p>
              <p className="mt-4 max-w-xl text-xs font-medium uppercase tracking-[0.2em] text-[var(--od-text-tertiary)] sm:text-[0.78rem]">
                先看看大家现在都在聊什么，再慢慢往下挖呀。
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 self-start lg:max-w-[24rem] lg:justify-end">
              <button
                type="button"
                onClick={() => navigate('/draw')}
                className="od-inline-action od-inline-action-primary"
              >
                <Dices className="h-4 w-4" />
                进入随机抽卡
              </button>
              <button
                type="button"
                onClick={() => navigate('/booklists')}
                className="od-inline-action od-inline-action-ghost"
              >
                <Plus className="h-4 w-4" />
                去书单页
              </button>
            </div>
          </div>

          <div className="w-full">
            {bannersQuery.isLoading ? (
              <div className="h-48 w-full animate-pulse rounded-[1.35rem] bg-[var(--od-surface-input)] xl:h-64" />
            ) : bannersQuery.data && bannersQuery.data.length > 0 ? (
              <BannerCarousel
                banners={bannersQuery.data.map((b) => ({
                  id: b.thread_id,
                  image: b.cover_image_url,
                  title: b.title,
                  description: b.author ? `作者：${b.author.display_name || b.author.global_name || b.author.name}` : '点击可以直接探索原帖',
                }))}
                onBannerClick={(banner) => {
                  const url = `https://discord.com/channels/${GUILD_ID}/${banner.id}`;
                  window.open(url, '_blank', 'noopener,noreferrer');
                }}
              />
            ) : (
              <div className="py-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-[var(--od-text-tertiary)]">Featured Thread</p>
                <p className="text-lg font-semibold text-[var(--od-text-primary)]">当前没有可展示的 Banner。</p>
                <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">没关系呀，今天就先不摆头图了，我还是会继续把下面值得看的内容给你摊开。</p>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="px-1 py-8">


        <FluidDivider label="Discovery Feed" tone="strong" className="mb-6" />
        {plazaPreferencePatch && (
          <div className="mb-5">
            <div className="od-inline-notice" data-tone="accent">
              <div className="od-inline-notice-head">
                <div className="min-w-0">
                  <div className="od-editorial-kicker">
                    <Compass className="h-3.5 w-3.5" />
                    Preference Filter Active
                  </div>
                  <p className="od-inline-notice-title mt-3">我先按你的口味帮你筛过一遍啦</p>
                  <p className="od-inline-notice-copy mt-2 max-w-3xl">
                    那些你大概不会感兴趣的内容，我先帮你挡开了一点点。要是你今天想乱逛，也可以临时放开看看呀。
                  </p>
                </div>

                <div className="od-inline-notice-actions shrink-0 sm:justify-end">
                  <button
                    type="button"
                    onClick={() => setIgnorePreferenceFilter(true)}
                    className="od-inline-action od-inline-action-soft"
                  >
                    暂时忽略偏好
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate('/me?tab=preferences')}
                    className="od-inline-action od-inline-action-ghost"
                  >
                    去调整偏好
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        {!plazaPreferencePatch && ignorePreferenceFilter && preferences && (
          <div className="mb-5 flex justify-end">
            <button
              type="button"
              onClick={() => setIgnorePreferenceFilter(false)}
              className="od-inline-action od-inline-action-ghost"
            >
              恢复偏好过滤
            </button>
          </div>
        )}
        <div className="flex items-start gap-3 mt-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
            <Compass className="h-5 w-5" />
          </div>
          <div>
            <h2 className="od-section-title">正在发生</h2>
            <p className="mt-1 text-sm text-[var(--od-text-secondary)]">我把它们分成几条比较好逛的轨道啦，你可以先看新的，也可以挑热闹的那条慢慢翻。</p>
          </div>
        </div>
      </section>

      <section className="px-1">
        {PLAZA_RAILS.map((rail) => {
          const list = railResultMap[rail.key];
          if (!list || list.length === 0) return null;

          return (
            <div key={rail.key} className="od-page-section py-4 sm:py-5">
              <FluidDivider label={rail.title} className="mb-5" />
              <div className="mb-5 flex items-center justify-between gap-3">
                <div>
                  <h2 className="od-section-title">{rail.title}</h2>
                  <p className="mt-1 text-sm text-[var(--od-text-secondary)]">{rail.subtitle}</p>
                </div>
                <Link
                  to={`/?sort=${railSortMap[rail.key]}`}
                  className="od-inline-action od-inline-action-ghost"
                >
                  查看更多
                </Link>
              </div>

              <div className={gridClass}>
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

      <section className="px-1">
        <FluidDivider label="Booklists" tone="strong" className="mb-5" />
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <h2 className="od-section-title">书单精选</h2>
            <p className="mt-1 text-sm text-[var(--od-text-secondary)]">这些都是大家比较爱收的书单，我替你放在前面啦，说不定会刚好合你胃口。</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate('/booklists')}
              className="od-inline-action od-inline-action-ghost"
            >
              全部书单
            </button>
            <button
              type="button"
              onClick={() => navigate('/booklists')}
              className="od-inline-action od-inline-action-primary"
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
          <div className="rounded-[1.25rem] bg-[var(--od-surface-input)] p-6 text-sm text-[var(--od-text-secondary)]">
            这会儿还没有我想先塞给你的书单呢，晚点再来看看也许就有啦。
          </div>
        )}
      </section>

      <div className="px-1 text-xs text-[var(--od-text-tertiary)]">
        <div className="inline-flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[var(--od-accent)]" />
          这些内容是我按最近的热度和时间顺手排出来的，先给你一个好逛的起点呀。
        </div>
      </div>

    </div>
  );
}
