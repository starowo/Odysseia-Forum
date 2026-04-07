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
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-8 p-4 sm:p-6 lg:p-8">
      <section className="od-page-hero min-h-[26rem]">
        {heroBanner ? (
          <button
            type="button"
            onClick={() => setPreviewThreadId(heroBanner.thread_id)}
            className="absolute inset-0 h-full w-full"
          >
            <img
              src={heroBanner.cover_image_url}
              alt={heroBanner.title}
              className="h-full w-full object-cover"
            />
          </button>
        ) : (
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(88,101,242,0.28),transparent_34%),linear-gradient(160deg,var(--od-surface-raised),var(--od-surface-shell))]" />
        )}

        <div className="od-page-hero-content flex h-full min-h-[26rem] flex-col justify-between p-6 sm:p-8 lg:p-10">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-white/82 backdrop-blur-sm">
                <Compass className="h-3.5 w-3.5" />
                Plaza Spotlight
              </div>
              <h1 className="od-hero-title max-w-2xl">内容广场</h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-white/80 sm:text-base sm:leading-7">
                把 Banner 曝光、趋势内容、编辑推荐和精选书单收拢成一个更连贯的阅读入口，减少卡片套卡片，让信息自己站出来。
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 self-start">
              <button
                type="button"
                onClick={() => navigate('/draw')}
                className="od-inline-action bg-white text-[var(--od-bg-primary)] transition-colors hover:bg-white/92"
              >
                <Dices className="h-4 w-4" />
                进入随机抽卡
              </button>
              <button
                type="button"
                onClick={() => setShowBannerApply(true)}
                className="od-inline-action od-inline-action-primary"
              >
                <Megaphone className="h-4 w-4" />
                申请 Banner
              </button>
              <button
                type="button"
                onClick={() => navigate('/booklists')}
                className="od-inline-action bg-black/18 text-white backdrop-blur-sm transition-colors hover:bg-black/28"
              >
                <Plus className="h-4 w-4" />
                去书单页
              </button>
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(18rem,0.9fr)] lg:items-end">
            <div className="max-w-2xl">
              {heroBanner ? (
                <button
                  type="button"
                  onClick={() => setPreviewThreadId(heroBanner.thread_id)}
                  className="text-left"
                >
                  <p className="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-white/62">Featured Thread</p>
                  <h2 className="max-w-xl text-2xl font-bold leading-tight tracking-tight text-white sm:text-3xl">
                    {heroBanner.title}
                  </h2>
                  <p className="mt-3 text-sm text-white/70">点击直接打开预览，进入更沉浸的详情阅读。</p>
                </button>
              ) : bannersQuery.isLoading ? (
                <div className="h-24 w-full animate-pulse rounded-2xl bg-white/10" />
              ) : (
                <div>
                  <p className="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-white/62">Featured Thread</p>
                  <p className="text-lg font-semibold text-white">当前没有可展示的 Banner。</p>
                </div>
              )}
            </div>

            <div className="rounded-[1.5rem] border border-white/10 bg-black/18 p-4 backdrop-blur-sm">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-white/62">More Exposure</p>
              {bannersQuery.isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, idx) => (
                    <div key={idx} className="h-14 animate-pulse rounded-2xl bg-white/10" />
                  ))}
                </div>
              ) : secondaryBanners.length > 0 ? (
                <div className="space-y-2.5">
                  {secondaryBanners.map((banner, index) => (
                    <button
                      key={`${banner.thread_id}-${banner.cover_image_url}`}
                      type="button"
                      onClick={() => setPreviewThreadId(banner.thread_id)}
                      className="flex w-full items-start justify-between gap-3 rounded-2xl px-3 py-3 text-left transition-colors hover:bg-white/10"
                    >
                      <div className="min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/45">0{index + 2}</p>
                        <p className="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-white/88">{banner.title}</p>
                      </div>
                      <div className="h-12 w-12 shrink-0 overflow-hidden rounded-2xl border border-white/10 bg-black/20">
                        <img src={banner.cover_image_url} alt={banner.title} className="h-full w-full object-cover" />
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-white/65">更多 Banner 位暂时空缺。</p>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="px-1">
        <div className="mb-8 overflow-hidden rounded-[1.6rem] border border-[color-mix(in_srgb,var(--od-accent)_16%,transparent)] bg-[linear-gradient(140deg,color-mix(in_srgb,var(--od-accent)_9%,transparent),color-mix(in_srgb,var(--od-surface-raised)_92%,black_8%))] p-5 sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-[color-mix(in_srgb,var(--od-accent)_18%,transparent)] bg-[color-mix(in_srgb,var(--od-accent)_10%,transparent)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--od-accent)]">
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
        </div>

        <FluidDivider label="Discovery Feed" tone="strong" className="mb-6" />
        {plazaPreferencePatch && (
          <div className="mb-5 flex flex-col gap-3 rounded-[1.35rem] border border-[color-mix(in_srgb,var(--od-accent)_18%,transparent)] bg-[color-mix(in_srgb,var(--od-accent)_7%,transparent)] px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-[var(--od-text-primary)]">广场已按你的频道与标签偏好收束</p>
              <p className="mt-1 text-xs leading-5 text-[var(--od-text-secondary)]">不喜欢的频道和标签会默认被拦在外面，你也可以临时取消看看完整广场。</p>
            </div>
            <button
              type="button"
              onClick={() => setIgnorePreferenceFilter(true)}
              className="od-inline-action od-inline-action-ghost"
            >
              暂时忽略偏好
            </button>
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
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
            <Compass className="h-5 w-5" />
          </div>
          <div>
            <h2 className="od-section-title">正在发生</h2>
            <p className="mt-1 text-sm text-[var(--od-text-secondary)]">按发布时间、反应、讨论度和编辑选择整理的四条内容轨道。</p>
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

      <section className="px-1">
        <FluidDivider label="Booklists" tone="strong" className="mb-5" />
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <h2 className="od-section-title">书单精选</h2>
            <p className="mt-1 text-sm text-[var(--od-text-secondary)]">按收藏热度筛选的优质合集。</p>
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
