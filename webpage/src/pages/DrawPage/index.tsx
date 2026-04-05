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
import { GUILD_ID, CHANNELS, CHANNEL_CATEGORIES } from '@/shared/config/channelCategories.private';
import { FluidDivider } from '@/shared/ui/FluidDivider';
import { ThreadPreviewOverlay } from '@/widgets/thread-preview/ThreadPreviewOverlay';

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

const allChannels = CHANNEL_CATEGORIES.flatMap((category) => category.channels);

export function DrawPage() {
  const navigate = useNavigate();
  const { preferences } = useUserPreferences({ guildId: GUILD_ID });
  const preferenceContext = useMemo(
    () => getDiscoveryPreferenceContext(preferences),
    [preferences],
  );

  const [scopeMode, setScopeMode] = useState<DrawScopeMode>('preferences');
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [previewThread, setPreviewThread] = useState<Thread | null>(null);
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
  const scopeSignature = effectiveChannelIds?.join(',') || 'all-channels';

  const candidateQuery = useQuery({
    queryKey: ['draw', 'candidate-pool', preferenceSignature, scopeMode, selectedChannelId, scopeSignature],
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
  const drawChannelName = selectedChannelId ? CHANNELS[selectedChannelId] || '未命名频道' : '';
  const activeScopeLabel = scopeMode === 'channel' && drawChannelName
    ? `频道 · ${drawChannelName}`
    : preferenceContext?.preferredChannelIds.length
      ? `偏好频道 · ${preferenceContext.preferredChannelIds.length} 个`
      : '全社区发现池';

  const handleDraw = (count: number) => {
    const sampled = sampleThreads(candidateThreads, count);
    setLastDrawCount(count);
    setDrawResults(sampled);
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-8 p-4 sm:p-6 lg:p-8">
      <section className="relative overflow-hidden rounded-[2rem] border border-[var(--od-shell-line)] bg-[linear-gradient(155deg,color-mix(in_srgb,var(--od-accent)_16%,var(--od-surface-shell)),color-mix(in_srgb,var(--od-surface-raised)_92%,black_8%))] p-6 shadow-[var(--od-shadow-soft)] sm:p-8 lg:p-10">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.22),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(255,208,92,0.14),transparent_24%)]" />
        <div className="relative z-10 grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_22rem] lg:items-end">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/12 bg-black/18 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-white/84 backdrop-blur-sm">
              <Sparkles className="h-3.5 w-3.5" />
              Surprise Discovery Ritual
            </div>
            <h1 className="od-hero-title max-w-3xl text-white">随机抽卡</h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/78 sm:text-base sm:leading-7">
              把广场式发现变成一次有仪式感的揭晓体验。抽到的内容只会来自你的偏好允许范围，频道越明确，结果越聚焦。
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-2 text-xs text-white/74">
              <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/10 px-3 py-1.5">
                <BadgeCheck className="h-3.5 w-3.5" />
                {preferenceContext ? '偏好过滤已生效' : '尚未设置偏好，当前使用全社区池'}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/10 px-3 py-1.5">
                <Layers3 className="h-3.5 w-3.5" />
                当前范围：{activeScopeLabel}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/10 px-3 py-1.5">
                <Dices className="h-3.5 w-3.5" />
                候选 {candidateThreads.length} 条
              </span>
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-white/10 bg-black/18 p-4 backdrop-blur-md">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-white">进入方式</p>
                <p className="mt-1 text-xs leading-5 text-white/62">抽卡范围不会越过你的发现偏好。</p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/')}
                className="od-inline-action bg-white/10 text-white transition-colors hover:bg-white/16"
              >
                <Compass className="h-4 w-4" />
                回广场
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-white/48">抽卡范围</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setScopeMode('preferences')}
                    className={`rounded-2xl px-4 py-3 text-left text-sm transition-colors ${
                      scopeMode === 'preferences'
                        ? 'bg-white text-[var(--od-bg-primary)]'
                        : 'bg-white/8 text-white hover:bg-white/14'
                    }`}
                  >
                    按我的偏好抽
                  </button>
                  <button
                    type="button"
                    onClick={() => setScopeMode('channel')}
                    className={`rounded-2xl px-4 py-3 text-left text-sm transition-colors ${
                      scopeMode === 'channel'
                        ? 'bg-white text-[var(--od-bg-primary)]'
                        : 'bg-white/8 text-white hover:bg-white/14'
                    }`}
                  >
                    指定频道抽
                  </button>
                </div>
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-white/48">频道选择</p>
                <select
                  value={scopeMode === 'channel' ? selectedChannelId : ''}
                  onChange={(event) => setSelectedChannelId(event.target.value)}
                  disabled={scopeMode !== 'channel' || availableScopeChannels.length === 0}
                  className="w-full rounded-2xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-white outline-none transition-colors disabled:cursor-not-allowed disabled:opacity-45"
                >
                  {availableScopeChannels.length === 0 ? (
                    <option value="">当前没有可抽取频道</option>
                  ) : (
                    availableScopeChannels.map((channel) => (
                      <option key={channel.id} value={channel.id} className="text-black">
                        {channel.name}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  disabled={candidateThreads.length === 0 || candidateQuery.isLoading}
                  onClick={() => handleDraw(1)}
                  className="od-inline-action w-full justify-center bg-white text-[var(--od-bg-primary)] transition-colors hover:bg-white/92 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Wand2 className="h-4 w-4" />
                  来一抽
                </button>
                <button
                  type="button"
                  disabled={candidateThreads.length === 0 || candidateQuery.isLoading}
                  onClick={() => handleDraw(10)}
                  className="od-inline-action w-full justify-center bg-white/12 text-white transition-colors hover:bg-white/18 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Dices className="h-4 w-4" />
                  十连发现
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-[1.35rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-raised)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--od-text-tertiary)]">频道池</p>
          <p className="mt-3 text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">
            {effectiveChannelIds?.length ?? allChannels.length}
          </p>
          <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
            {preferenceContext?.preferredChannelIds.length
              ? '抽卡只会从你的偏好频道里取材，指定频道时会进一步收缩范围。'
              : '你还没有设定偏好频道，所以当前候选池来自全部公开频道。'}
          </p>
        </div>
        <div className="rounded-[1.35rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-raised)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--od-text-tertiary)]">标签约束</p>
          <p className="mt-3 text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">
            {(includeTags?.length || 0) + (excludeTags?.length || 0)}
          </p>
          <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
            包含标签 {includeTags?.length || 0} 个，排除标签 {excludeTags?.length || 0} 个。抽卡不会越过这些边界。
          </p>
        </div>
        <div className="rounded-[1.35rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-raised)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--od-text-tertiary)]">当前池深度</p>
          <p className="mt-3 text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">{candidateThreads.length}</p>
          <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
            这是本轮可参与抽取的内容数。候选池越大，随机性越强；越小，越接近定向发现。
          </p>
        </div>
      </section>

      <section>
        <FluidDivider label="Pool Status" tone="strong" className="mb-6" />
        {candidateQuery.isLoading ? (
          <div className="rounded-[1.5rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-input)] p-8 text-sm text-[var(--od-text-secondary)]">
            正在整理抽卡候选池…
          </div>
        ) : candidateQuery.isError ? (
          <div className="rounded-[1.5rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-input)] p-8">
            <p className="text-base font-semibold text-[var(--od-text-primary)]">候选池加载失败</p>
            <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">当前无法生成抽卡范围，稍后可以重试一次。</p>
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
          <div className="rounded-[1.5rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-input)] p-8">
            <p className="text-base font-semibold text-[var(--od-text-primary)]">当前范围里没有可抽取内容</p>
            <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
              可以先放宽频道范围，或者去 `偏好` 页面调整标签限制后再回来。
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
          <div className="rounded-[1.5rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-raised)] p-5 text-sm text-[var(--od-text-secondary)]">
            现在可以开始抽了。单抽适合快速开盲盒，十连更适合一次看完整批次的灵感落点。
          </div>
        )}
      </section>

      <section>
        <FluidDivider label="Reveal" tone="strong" className="mb-6" />
        {featuredResult ? (
          <div className="flex flex-col gap-6">
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1.18fr)_minmax(18rem,0.92fr)] lg:items-start">
              <div className="space-y-4">
                <div className="inline-flex w-fit items-center gap-2 rounded-full border border-[color-mix(in_srgb,var(--od-accent)_18%,transparent)] bg-[color-mix(in_srgb,var(--od-accent)_10%,transparent)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--od-accent)]">
                  <Sparkles className="h-3.5 w-3.5" />
                  {lastDrawCount > 1 ? '十连主卡' : '本次命中'}
                </div>

                <div className="max-w-[42rem]">
                  <ThreadCard thread={featuredResult} onPreview={setPreviewThread} />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPreviewThread(featuredResult)}
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
                      {drawResults.length > 1 ? '右侧保持和主卡同构，只缩成更紧凑的卡片列。' : '单抽模式下，这里会在多抽时展开其余结果。'}
                    </p>
                  </div>
                  {drawResults.length > 1 && (
                    <span className="rounded-full border border-[var(--od-shell-line)] bg-[var(--od-surface-soft)] px-3 py-1 text-[11px] font-semibold text-[var(--od-text-secondary)]">
                      已揭晓 {Math.max(0, revealedCount - 1)} / {Math.max(0, drawResults.length - 1)}
                    </span>
                  )}
                </div>

                {drawResults.length > 1 ? (
                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-2">
                    {trailingResults.map((thread, index) => (
                      <div key={thread.thread_id} className="animate-in fade-in zoom-in-95 duration-300" style={{ animationDelay: `${index * 90}ms` }}>
                        <ThreadCard thread={thread} onPreview={setPreviewThread} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-[1.5rem] border border-dashed border-[var(--od-shell-line)] bg-[var(--od-surface-input)] p-8 text-center text-sm text-[var(--od-text-secondary)]">
                    十连时，右侧会展开更多同构小卡；移动端则自动变成上主卡、下小卡的纵向堆叠。
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-[1.5rem] border border-dashed border-[var(--od-shell-line)] bg-[var(--od-surface-input)] p-10 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
              <Sparkles className="h-7 w-7" />
            </div>
            <h3 className="mt-5 text-xl font-bold tracking-tight text-[var(--od-text-primary)]">第一张卡还在等你揭晓</h3>
            <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
              先选抽卡范围，再决定是单抽还是十连。结果会从当前偏好允许的池子里随机生成。
            </p>
          </div>
        )}
      </section>

      {previewThread && (
        <ThreadPreviewOverlay thread={previewThread} onClose={() => setPreviewThread(null)} />
      )}
    </div>
  );
}
