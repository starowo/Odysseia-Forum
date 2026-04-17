import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BadgeCheck,
  Compass,
  Dices,
  Eye,
  Layers3,
  RefreshCw,
  Sparkles,
  Wand2,
} from 'lucide-react';

import { ThreadCard } from '@/entities/thread/ThreadCard';
import type { Thread } from '@/entities/thread/types';
import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
import { getDiscoveryPreferenceContext } from '@/features/preferences/lib/discoveryPreferences';
import { searchApi } from '@/features/search/api/searchApi';
import { usePreviewThread } from '@/features/search/hooks/usePreviewThread';
import { searchKeys } from '@/features/search/lib/queryKeys';
import { GUILD_ID } from '@/shared/config/channelCategories.private';
import { useChannels } from '@/shared/hooks/useChannels';
import { FluidDivider } from '@/shared/ui/FluidDivider';

type DrawScopeMode = 'preferences' | 'channel';

const DRAW_BATCH_LIMIT = 72;

function uniqueThreads(threads: Thread[]) {
  const map = new Map<string, Thread>();
  for (const thread of threads) {
    if (!thread?.thread_id) continue;
    if (!map.has(thread.thread_id)) map.set(thread.thread_id, thread);
  }
  return Array.from(map.values());
}

function sampleThreads(threads: Thread[], count: number) {
  const pool = [...threads];
  for (let i = pool.length - 1; i > 0; i -= 1) {
    const swapIndex = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[swapIndex]] = [pool[swapIndex], pool[i]];
  }
  return pool.slice(0, Math.min(count, pool.length));
}

// allChannels moved to component context

export function DrawPage() {
  const navigate = useNavigate();
  const { openPreview } = usePreviewThread();
  const { preferences } = useUserPreferences({ guildId: GUILD_ID });
  const preferenceContext = useMemo(
    () => getDiscoveryPreferenceContext(preferences),
    [preferences],
  );
  
  const { data: channelsData } = useChannels();
  const allChannels = useMemo(() => {
    return channelsData?.channels || [];
  }, [channelsData?.channels]);

  const [scopeMode, setScopeMode] = useState<DrawScopeMode>('preferences');
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [drawResults, setDrawResults] = useState<Thread[]>([]);
  const [lastDrawCount, setLastDrawCount] = useState<number>(1);
  const [revealedCount, setRevealedCount] = useState<number>(0);

  const preferredChannelIds = preferenceContext?.preferredChannelIds || [];
  const availableScopeChannels = useMemo(() => {
    if (preferredChannelIds.length === 0) return allChannels;

    const preferredSet = new Set(preferredChannelIds);
    return allChannels.filter((channel) => preferredSet.has(channel.id));
  }, [preferredChannelIds]);

  useEffect(() => {
    if (scopeMode !== 'channel') return;

    if (!selectedChannelId) {
      const fallback = availableScopeChannels[0]?.id || '';
      if (fallback) setSelectedChannelId(fallback);
      return;
    }

    if (!availableScopeChannels.some((channel) => channel.id === selectedChannelId)) {
      setSelectedChannelId(availableScopeChannels[0]?.id || '');
    }
  }, [availableScopeChannels, scopeMode, selectedChannelId]);

  useEffect(() => {
    if (drawResults.length === 0) {
      setRevealedCount(0);
      return;
    }

    setRevealedCount(1);
    if (drawResults.length === 1) return;

    const timers = drawResults.slice(1).map((_, index) =>
      window.setTimeout(() => {
        setRevealedCount((current) => Math.min(drawResults.length, current + 1));
      }, 180 * (index + 1)),
    );

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [drawResults]);

  const effectiveChannelIds = useMemo(() => {
    if (scopeMode === 'channel' && selectedChannelId) return [selectedChannelId];
    return preferenceContext?.preferredChannelIds.length
      ? preferenceContext.preferredChannelIds
      : undefined;
  }, [preferenceContext?.preferredChannelIds, scopeMode, selectedChannelId]);

  const includeTags = preferenceContext?.includeTags.length ? preferenceContext.includeTags : undefined;
  const excludeTags = preferenceContext?.excludeTags.length ? preferenceContext.excludeTags : undefined;
  const preferenceSignature = preferenceContext?.signature || 'all-content';
  const candidateQuery = useQuery({
    queryKey: searchKeys.drawPool({
      preferenceSignature,
      scopeMode,
      selectedChannelId,
      effectiveChannelIds,
    }),
    queryFn: async () => {
      const result = await searchApi.search({
        channel_ids: effectiveChannelIds,
        include_tags: includeTags,
        exclude_tags: excludeTags,
        sort_method: 'last_active_desc',
        limit: DRAW_BATCH_LIMIT,
      });

      return uniqueThreads((result.results || []) as Thread[]);
    },
    staleTime: 60 * 1000,
  });

  const candidateThreads = candidateQuery.data || [];
  const featuredResult = drawResults[0] || null;
  const trailingResults = drawResults.slice(1, revealedCount);
  const activeScopeLabel = scopeMode === 'channel' && selectedChannelId
    ? availableScopeChannels.find((c) => c.id === selectedChannelId)?.name || '未找到频道'
    : '我的偏好池范围';


  const handleDraw = (count: number) => {
    const sampled = sampleThreads(candidateThreads, count);
    setLastDrawCount(count);
    setDrawResults(sampled);
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-8 p-4 sm:p-6 lg:p-8">
      <section className="relative p-2 sm:p-6 lg:p-8">
        <div className="relative z-10 flex flex-col gap-10 max-w-4xl">
          <div>
            <div className="od-editorial-kicker mb-4 text-[var(--od-text-tertiary)]">
              <Sparkles className="h-3.5 w-3.5" />
              Surprise Discovery Ritual
            </div>
            <h1 className="od-hero-title max-w-3xl text-[var(--od-text-primary)]">随机抽卡</h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)] sm:text-base sm:leading-7">
              你要是懒得自己翻，我就帮你抽呀。抽出来的内容像拆小盲盒一样，一张张看会很有意思呢。
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-2 text-xs text-[var(--od-text-secondary)]">
              <span className="inline-flex items-center gap-1 rounded-full border border-[var(--od-border)] bg-[var(--od-surface-input)] px-3 py-1.5">
                <BadgeCheck className="h-3.5 w-3.5 text-[var(--od-accent)]" />
                {preferenceContext ? '偏好过滤已生效' : '尚未设置偏好，当前使用全社区池'}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-[var(--od-border)] bg-[var(--od-surface-input)] px-3 py-1.5">
                <Layers3 className="h-3.5 w-3.5 text-[var(--od-accent)]" />
                当前范围：{activeScopeLabel}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-[var(--od-border)] bg-[var(--od-surface-input)] px-3 py-1.5">
                <Dices className="h-3.5 w-3.5 text-[var(--od-accent)]" />
                候选 {candidateThreads.length} 条
              </span>
            </div>
          </div>

          <div className="space-y-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--od-text-label)]">Draw Flow</p>
                <p className="mt-2 text-sm font-semibold text-[var(--od-text-primary)]">先圈个大概范围，再决定抽一张还是抽十张</p>
                <p className="mt-1 text-xs leading-5 text-[var(--od-text-secondary)]">我不会故意抽到你偏好外面去的，放心吧。</p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/')}
                className="od-inline-action od-inline-action-ghost"
              >
                <Compass className="h-4 w-4" />
                回广场
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">抽卡范围</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setScopeMode('preferences')}
                    className={`rounded-2xl border px-4 py-3 text-left text-sm transition-colors ${
                      scopeMode === 'preferences'
                        ? 'border-[var(--od-accent)] bg-[var(--od-surface-input)] text-[var(--od-accent)] shadow-sm'
                        : 'border-[var(--od-border)] bg-[var(--od-surface-input)] text-[var(--od-text-secondary)] hover:border-[var(--od-accent)]/50'
                     }`}
                  >
                    按我的偏好抽
                  </button>
                  <button
                    type="button"
                    onClick={() => setScopeMode('channel')}
                    className={`rounded-2xl border px-4 py-3 text-left text-sm transition-colors ${
                      scopeMode === 'channel'
                        ? 'border-[var(--od-accent)] bg-[var(--od-surface-input)] text-[var(--od-accent)] shadow-sm'
                        : 'border-[var(--od-border)] bg-[var(--od-surface-input)] text-[var(--od-text-secondary)] hover:border-[var(--od-accent)]/50'
                    }`}
                  >
                    指定频道抽
                  </button>
                </div>
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">频道选择</p>
                <select
                  value={scopeMode === 'channel' ? selectedChannelId : ''}
                  onChange={(event) => setSelectedChannelId(event.target.value)}
                  disabled={scopeMode !== 'channel' || availableScopeChannels.length === 0}
                  className="w-full rounded-2xl border border-[var(--od-border)] bg-[var(--od-surface-input)] px-4 py-3 text-sm text-[var(--od-text-primary)] outline-none transition-colors disabled:cursor-not-allowed disabled:opacity-45 focus:border-[var(--od-accent)]"
                >
                  {availableScopeChannels.length === 0 ? (
                    <option value="">当前没有可抽取频道</option>
                  ) : (
                    availableScopeChannels.map((channel) => (
                      <option key={channel.id} value={channel.id} className="text-[var(--od-text-primary)]">
                        {channel.name}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div className="pt-2">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">揭晓方式</p>
                <p className="mt-2 text-xs leading-5 text-[var(--od-text-secondary)]">想随手碰碰运气就单抽，想一次看热闹一点就十连呀。</p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  disabled={candidateThreads.length === 0 || candidateQuery.isLoading}
                  onClick={() => handleDraw(1)}
                  className="od-inline-action od-inline-action-primary w-full justify-center disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Wand2 className="h-4 w-4" />
                  来一抽
                </button>
                <button
                  type="button"
                  disabled={candidateThreads.length === 0 || candidateQuery.isLoading}
                  onClick={() => handleDraw(10)}
                  className="od-inline-action od-inline-action-soft w-full justify-center disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Dices className="h-4 w-4" />
                  十连发现
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-1">
        <FluidDivider label="Pool Summary" tone="strong" className="mb-6" />
        <div className="od-metric-strip">
          <div className="od-metric-line">
            <p className="od-metric-line-label">频道池</p>
            <p className="od-metric-line-value">{effectiveChannelIds?.length ?? allChannels.length}</p>
            <p className="od-metric-line-note">
              {preferenceContext?.preferredChannelIds.length
                ? '我会优先从你平时更常看的频道里翻，指定频道以后范围还会再收一点。'
                : '你还没给我偏好范围呢，所以我现在是从公开频道里一起翻。'}
            </p>
          </div>
          <div className="od-metric-line">
            <p className="od-metric-line-label">标签约束</p>
            <p className="od-metric-line-value">{(includeTags?.length || 0) + (excludeTags?.length || 0)}</p>
            <p className="od-metric-line-note">现在记着包含标签 {includeTags?.length || 0} 个、排除标签 {excludeTags?.length || 0} 个，我会乖乖照着这个边界来抽的。</p>
          </div>
          <div className="od-metric-line">
            <p className="od-metric-line-label">当前池深度</p>
            <p className="od-metric-line-value">{candidateThreads.length}</p>
            <p className="od-metric-line-note">这里就是这一轮能被抽到的总数啦。池子越大越像乱逛，池子越小就越像冲着某种口味去找。</p>
          </div>
        </div>
      </section>

      <section>
        <FluidDivider label="Pool Status" tone="strong" className="mb-6" />
        {candidateQuery.isLoading ? (
          <div className="od-draw-slot text-sm text-[var(--od-text-secondary)]">
            正在整理抽卡候选池…
          </div>
        ) : candidateQuery.isError ? (
          <div className="od-draw-slot">
            <p className="text-base font-semibold text-[var(--od-text-primary)]">候选池加载失败了</p>
            <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">哎呀，没有拉到数据，稍后帮你重试一次吧。</p>
            <button
              type="button"
              onClick={() => candidateQuery.refetch()}
              className="od-inline-action od-inline-action-primary mt-4"
            >
              <RefreshCw className="h-4 w-4" />
              重试
            </button>
          </div>
        ) : candidateThreads.length === 0 ? (
          <div className="od-draw-slot">
            <p className="text-base font-semibold text-[var(--od-text-primary)]">当前范围里没有可抽取内容</p>
            <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
              可以放宽频道范围，或者去偏好页调整一下标签限制，再回来找我抽卡～
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setScopeMode('preferences')}
                className="od-inline-action od-inline-action-ghost"
              >
                恢复默认范围
              </button>
              <button
                type="button"
                onClick={() => navigate('/me?tab=preferences')}
                className="od-inline-action od-inline-action-soft"
              >
                去调整偏好
              </button>
            </div>
          </div>
        ) : (
          <div className="od-draw-slot text-sm text-[var(--od-text-secondary)]">
            准备好啦。你想先轻轻试一张也行，想热闹一点直接十连也行，我都陪你。
          </div>
        )}
      </section>

      <section>
        <FluidDivider label="Reveal" tone="strong" className="mb-6" />
        {featuredResult ? (
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-12">
              <div className="space-y-4">
                <div className="inline-flex w-fit items-center gap-2 rounded-full border border-[color-mix(in_srgb,var(--od-accent)_18%,transparent)] bg-[color-mix(in_srgb,var(--od-accent)_10%,transparent)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--od-accent)]">
                  <Sparkles className="h-3.5 w-3.5" />
                  {lastDrawCount > 1 ? '十连主卡' : '本次命中'}
                </div>

                <div className="w-full lg:max-w-4xl">
                  <ThreadCard thread={featuredResult} onPreview={openPreview} />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => openPreview(featuredResult)}
                    className="od-inline-action od-inline-action-primary"
                  >
                    <Eye className="h-4 w-4" />
                    打开预览
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDraw(lastDrawCount)}
                    className="od-inline-action od-inline-action-soft"
                  >
                    <RefreshCw className="h-4 w-4" />
                    再抽一次
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate(`/search?channel=${featuredResult.channel_id}`)}
                    className="od-inline-action od-inline-action-ghost"
                  >
                    <Compass className="h-4 w-4" />
                    去该频道继续逛
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[var(--od-text-primary)]">其余结果</p>
                    <p className="mt-1 text-xs leading-5 text-[var(--od-text-secondary)]">
                      {drawResults.length > 1 ? '剩下那些我也整整齐齐摆在旁边啦，你可以一起对着看。' : '现在是单抽，所以这里只会在多抽的时候热闹起来。'}
                    </p>
                  </div>
                  {drawResults.length > 1 && (
                    <span className="rounded-full border border-[var(--od-shell-line)] bg-[var(--od-surface-soft)] px-3 py-1 text-[11px] font-semibold text-[var(--od-text-secondary)]">
                      已揭晓 {Math.max(0, revealedCount - 1)} / {Math.max(0, drawResults.length - 1)}
                    </span>
                  )}
                </div>

                {drawResults.length > 1 ? (
                  <div className="flex overflow-x-auto snap-x snap-mandatory gap-4 pb-6 scrollbar-none -mx-4 px-4 sm:mx-0 sm:px-0">
                    {trailingResults.map((thread, index) => (
                      <div key={thread.thread_id} className="w-[18rem] shrink-0 snap-start animate-in fade-in zoom-in-95 duration-300" style={{ animationDelay: `${index * 90}ms` }}>
                        <ThreadCard thread={thread} onPreview={openPreview} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="od-draw-slot od-draw-slot-muted text-center text-sm text-[var(--od-text-secondary)]">
                    等你十连的时候，这里就会一下子铺开很多张，看起来会更有抽卡的感觉哦。
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="od-draw-slot od-draw-slot-muted p-10 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
              <Sparkles className="h-7 w-7" />
            </div>
            <h3 className="mt-5 text-xl font-bold tracking-tight text-[var(--od-text-primary)]">第一张卡还在等你揭晓哦～</h3>
            <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
              先挑一下这轮想在哪片地方碰运气，再决定抽一张还是十张。我会把结果乖乖送到你面前的。
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
