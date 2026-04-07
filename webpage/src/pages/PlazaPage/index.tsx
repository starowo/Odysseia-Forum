import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Compass, Dices, Megaphone, Plus, Sparkles } from 'lucide-react';

import { ThreadCard } from '@/entities/thread/ThreadCard';
import { BooklistCard } from '@/entities/booklist/BooklistCard';
import type { Booklist } from '@/entities/booklist/types';
import { plazaApi, PLAZA_RAILS, type PlazaRailKey } from '@/features/plaza/api/plazaApi';
import { BannerApplicationModal } from '@/features/banner/components/BannerApplicationModal';
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
  const setPreviewThreadId = usePreviewStore((state) => state.setPreviewThreadId);
  const setPreviewThread = usePreviewStore((state) => state.setPreviewThread);
  const { preferences } = useUserPreferences({ guildId: GUILD_ID });

  const [showBannerApply, setShowBannerApply] = useState(false);
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

  const heroBanner = bannersQuery.data?.[0] ?? null;
  const secondaryBanners = bannersQuery.data?.slice(1, 4) ?? [];

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-10 p-4 sm:p-6 lg:p-8">
      <section className="relative min-h-[22rem]">
        {heroBanner && (
          <button
            type="button"
            onClick={() => setPreviewThreadId(heroBanner.thread_id)}
            className="absolute inset-x-0 top-0 h-48 w-full opacity-20 mask-image-linear-to-b"
          >
            <img
              src={heroBanner.cover_image_url}
              alt={heroBanner.title}
              className="h-full w-full object-cover"
            />
          </button>
        )}

        <div className="relative z-10 flex flex-col justify-between pt-6 sm:pt-8 lg:pt-10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between mb-8">
            <div className="max-w-3xl">
              <div className="od-editorial-kicker mb-3 text-[var(--od-text-tertiary)]">
                <Compass className="h-3.5 w-3.5" />
                Plaza Spotlight
              </div>
              <h1 className="od-hero-title max-w-2xl text-[var(--od-text-primary)]">内容广场</h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)] sm:text-base sm:leading-7">
                把 Banner 曝光、趋势内容、编辑推荐和精选书单收拢成一个更连贯的阅读入口，减少卡片套卡片，让信息自己站出来。
              </p>
              <p className="mt-4 max-w-xl text-xs font-medium uppercase tracking-[0.2em] text-[var(--od-text-tertiary)] sm:text-[0.78rem]">
                先看当下最值得点开的内容，再顺着趋势轨道继续深入。
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
                onClick={() => setShowBannerApply(true)}
                className="od-inline-action od-inline-action-soft"
              >
                <Megaphone className="h-4 w-4" />
                申请 Banner
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

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(18rem,0.92fr)] lg:items-end">
            <div className="max-w-2xl">
              {heroBanner ? (
                <button
                  type="button"
                  onClick={() => setPreviewThreadId(heroBanner.thread_id)}
                  className="text-left py-4 transition-transform duration-200 hover:-translate-y-0.5 group"
                >
                  <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-[var(--od-text-tertiary)]">Featured Thread</p>
                  <h2 className="max-w-xl text-2xl font-bold leading-tight tracking-tight text-[var(--od-text-primary)] group-hover:text-[var(--od-accent)] sm:text-3xl">
                    {heroBanner.title}
                  </h2>
                  <p className="mt-3 max-w-lg text-sm leading-6 text-[var(--od-text-secondary)]">点击直接打开预览，先从这张头条封面进入，再沿着广场的轨道继续深挖。</p>
                </button>
              ) : bannersQuery.isLoading ? (
                <div className="h-28 w-full animate-pulse rounded-[1.35rem] bg-[var(--od-surface-input)]" />
              ) : (
                <div className="py-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-[var(--od-text-tertiary)]">Featured Thread</p>
                  <p className="text-lg font-semibold text-[var(--od-text-primary)]">当前没有可展示的 Banner。</p>
                  <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">广场仍会继续按趋势轨道和精选书单向下展开，不会因为头图空缺而中断发现节奏。</p>
                </div>
              )}
            </div>

            <div className="text-[var(--od-text-secondary)]">
              <div className="mb-4 flex items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--od-text-label)]">More Exposure</p>
                  <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">其余副位保持轻量榜单感，不再单独做成厚重的侧栏卡片。</p>
                </div>
                <Sparkles className="h-4 w-4 text-[var(--od-text-tertiary)]" />
              </div>
              {bannersQuery.isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, idx) => (
                    <div key={idx} className="h-14 animate-pulse rounded-[1.1rem] bg-[var(--od-surface-input)]" />
                  ))}
                </div>
              ) : secondaryBanners.length > 0 ? (
                <div className="space-y-1.5">
                  {secondaryBanners.map((banner, index) => (
                    <button
                      key={`${banner.thread_id}-${banner.cover_image_url}`}
                      type="button"
                      onClick={() => setPreviewThreadId(banner.thread_id)}
                      className="od-spotlight-item w-full text-left"
                    >
                      <div className="min-w-0">
                        <p className="od-spotlight-item-index text-[var(--od-text-tertiary)]">0{index + 2}</p>
                        <p className="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-[var(--od-text-primary)]">{banner.title}</p>
                      </div>
                      <div className="h-12 w-12 shrink-0 overflow-hidden rounded-[1rem] border border-[var(--od-border)] bg-[var(--od-surface-input)]">
                        <img src={banner.cover_image_url} alt={banner.title} className="h-full w-full object-cover" />
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-sm leading-6 text-[var(--od-text-secondary)]">更多 Banner 位暂时空缺，等新的内容冲上来之后，这里会继续补位。</p>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="px-1 py-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-2">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--od-accent)] bg-[var(--od-surface-soft)]">
                <Dices className="h-3.5 w-3.5" />
                Surprise Mode
              </div>
              <h2 className="mt-4 text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">不想挑的话，就让抽卡替你开路</h2>
              <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
                新的随机抽卡页已经上线，默认只会从你的偏好允许范围里取材。既能单抽，也能十连，把发现流做成一次更有仪式感的揭晓。
              </p>
            </div>

            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => navigate('/draw')}
                className="od-inline-action od-inline-action-primary"
              >
                <Dices className="h-4 w-4" />
                按偏好来一抽
              </button>
              <button
                type="button"
                onClick={() => navigate('/draw')}
                className="od-inline-action od-inline-action-ghost"
              >
                十连发现
              </button>
            </div>
          </div>

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
                  <p className="od-inline-notice-title mt-3">广场已经按你的偏好筛了一遍</p>
                  <p className="od-inline-notice-copy mt-2 max-w-3xl">
                    不感兴趣的频道和标签已经帮你挡掉了，想看看完整广场也可以临时取消。
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
            <p className="mt-1 text-sm text-[var(--od-text-secondary)]">帮你整理了四条内容轨道：最新发布、热门反应、讨论活跃和编辑精选。</p>
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
            <p className="mt-1 text-sm text-[var(--od-text-secondary)]">大家收藏最多的书单合集，看看有没有合你口味的。</p>
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
            暂无可推荐书单。
          </div>
        )}
      </section>

      <div className="px-1 text-xs text-[var(--od-text-tertiary)]">
        <div className="inline-flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[var(--od-accent)]" />
          推荐由综合排序 + 时间窗规则生成，后续将加入个性化权重。
        </div>
      </div>

      <BannerApplicationModal isOpen={showBannerApply} onClose={() => setShowBannerApply(false)} />
    </div>
  );
}
