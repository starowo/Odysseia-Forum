import { useEffect, useMemo, useState, type ComponentType } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Bookmark, FileText, Heart, RefreshCw, Save, Search, Settings2 } from 'lucide-react';
import { toast } from 'sonner';

import { UserHeaderCard } from '@/entities/user/UserHeaderCard';
import { UserStatsGrid } from '@/entities/user/UserStatsGrid';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { ThreadResultsCollection } from '@/entities/thread/ThreadResultsCollection';
import type { Thread } from '@/entities/thread/types';
import { useFollowsFeed } from '@/features/follows/hooks/useFollowsData';
import { searchApi } from '@/features/search/api/searchApi';
import { BooklistCard } from '@/entities/booklist/BooklistCard';
import type { Booklist } from '@/entities/booklist/types';
import {
  useCollectedBooklistsList,
  useCreateBooklist,
  useDeleteBooklist,
  useMyBooklistsList,
  useToggleBooklistCollection,
  useUpdateBooklist,
} from '@/features/booklists/hooks/useBooklistsData';
import { BooklistFormModal } from '@/features/booklists/components/BooklistFormModal';
import { usePreviewThread } from '@/features/search/hooks/usePreviewThread';
import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
import { PreferenceTagSelector } from '@/features/preferences/components/PreferenceTagSelector';
import { FluidDivider } from '@/shared/ui/FluidDivider';
import {
  toPreferencesFormValue,
  toPreferencesUpdatePayload,
  type PreferencesFormValue,
} from '@/features/preferences/lib/preferencesMapper';
import { CHANNEL_CATEGORIES } from '@/shared/config/navigation';
import { GUILD_ID } from '@/shared/config/channelCategories.private';

type MeTab = 'booklists' | 'follows' | 'threads' | 'preferences';
type BooklistSubTab = 'mine' | 'collected';

const DEFAULT_FORM: PreferencesFormValue = {
  preferredChannelIds: [],
  includeTagsText: '',
  excludeTagsText: '',
  includeKeywordsText: '',
  excludeKeywordsText: '',
  previewImageMode: 'thumbnail',
  resultsPerPage: 24,
  sortMethod: 'last_active_desc',
};

const tabOptions: Array<{ key: MeTab; label: string; icon: ComponentType<{ className?: string }> }> = [
  { key: 'booklists', label: '书单', icon: BookOpen },
  { key: 'follows', label: '关注', icon: Bookmark },
  { key: 'threads', label: '创建', icon: FileText },
  { key: 'preferences', label: '偏好', icon: Settings2 },
];

function parseTab(value: string | null): MeTab {
  if (value === 'booklists' || value === 'follows' || value === 'threads' || value === 'preferences') {
    return value;
  }
  return 'booklists';
}

function parseBooklistSubTab(value: string | null): BooklistSubTab {
  return value === 'collected' ? 'collected' : 'mine';
}

export function MePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const { openPreview } = usePreviewThread();

  const tab = parseTab(searchParams.get('tab'));
  const booklistSubTab = parseBooklistSubTab(searchParams.get('booklists'));

  const [showCreateBooklist, setShowCreateBooklist] = useState(false);
  const [editingBooklist, setEditingBooklist] = useState<Booklist | null>(null);

  const {
    preferences,
    isLoading: isPrefsLoading,
    isFetching: isPrefsFetching,
    savePreferences,
    isSaving,
  } = useUserPreferences({ guildId: GUILD_ID });

  const [form, setForm] = useState<PreferencesFormValue>(DEFAULT_FORM);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (isDirty) return;
    setForm(toPreferencesFormValue(preferences));
  }, [preferences, isDirty]);

  const channelOptions = useMemo(() => CHANNEL_CATEGORIES.flatMap((group) => group.channels), []);
  const { data: channelTagCatalog = [] } = useQuery({
    queryKey: ['me', 'preferences', 'channel-tag-catalog'],
    queryFn: () => searchApi.getChannelTagCatalog(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const availablePreferenceTags = useMemo(() => {
    const preferredChannels = new Set(form.preferredChannelIds);
    const scopedCatalog = preferredChannels.size > 0
      ? channelTagCatalog.filter((channel) => preferredChannels.has(channel.channel_id))
      : channelTagCatalog;

    const tagSet = new Set<string>();
    for (const channel of scopedCatalog) {
      for (const tag of channel.available_tags || []) {
        if (tag?.trim()) tagSet.add(tag.trim());
      }
      for (const tag of channel.virtual_tags || []) {
        if (tag?.trim()) tagSet.add(tag.trim());
      }
    }

    return Array.from(tagSet);
  }, [channelTagCatalog, form.preferredChannelIds]);

  const followsQuery = useFollowsFeed();

  const createdThreadsQuery = useQuery({
    queryKey: ['me', 'threads', user?.id],
    enabled: Boolean(user?.id),
    queryFn: () =>
      searchApi.search({
        include_authors: user?.id ? [user.id] : [],
        sort_method: 'created_desc',
        limit: 36,
      }),
    staleTime: 60 * 1000,
  });

  const myBooklistsQuery = useMyBooklistsList();

  const collectedBooklistsQuery = useCollectedBooklistsList();

  const collectMutation = useToggleBooklistCollection();

  const createMutation = useCreateBooklist(() => setShowCreateBooklist(false));

  const updateMutation = useUpdateBooklist(undefined, () => setEditingBooklist(null));

  const deleteMutation = useDeleteBooklist();

  const createdThreads = (createdThreadsQuery.data?.results || []) as Thread[];
  const totalReactions = createdThreads.reduce((sum, item) => sum + (Number(item.reaction_count) || 0), 0);
  const totalReplies = createdThreads.reduce((sum, item) => sum + (Number(item.reply_count) || 0), 0);
  const totalFollows = followsQuery.data?.total || 0;
  const totalBooklists = myBooklistsQuery.data?.total || 0;

  const stats = [
    {
      label: '我的书单',
      value: totalBooklists,
      icon: BookOpen,
    },
    {
      label: '我的关注',
      value: totalFollows,
      icon: Bookmark,
    },
    {
      label: '我的帖子',
      value: createdThreadsQuery.data?.total || 0,
      icon: FileText,
    },
    {
      label: '累计点赞',
      value: totalReactions,
      icon: Heart,
    },
  ];

  const setTab = (next: MeTab) => {
    const sp = new URLSearchParams(searchParams);
    sp.set('tab', next);
    setSearchParams(sp, { replace: true });
  };

  const setBooklistSubTab = (next: BooklistSubTab) => {
    const sp = new URLSearchParams(searchParams);
    sp.set('tab', 'booklists');
    sp.set('booklists', next);
    setSearchParams(sp, { replace: true });
  };

  const toggleChannel = (channelId: string) => {
    setIsDirty(true);
    setForm((prev) => {
      const exists = prev.preferredChannelIds.includes(channelId);
      return {
        ...prev,
        preferredChannelIds: exists
          ? prev.preferredChannelIds.filter((id) => id !== channelId)
          : [...prev.preferredChannelIds, channelId],
      };
    });
  };

  const savePreferenceForm = async () => {
    try {
      const payload = toPreferencesUpdatePayload(form);
      await savePreferences(payload);
      setIsDirty(false);
      toast.success('偏好已保存');
    } catch {
      toast.error('保存偏好失败');
    }
  };

  const activeBooklists = booklistSubTab === 'mine'
    ? myBooklistsQuery.data?.results || []
    : collectedBooklistsQuery.data?.results || [];

  return (
    <>
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-10 p-4 sm:p-6 lg:gap-14 lg:p-8">
        <section>
          <FluidDivider label="Me" tone="strong" className="mb-8 lg:mb-10" />
          <div className="flex flex-col gap-8">
            {user?.id && (
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => navigate(`/u/${user.id}`)}
                  className="od-inline-action od-inline-action-ghost w-full justify-center sm:w-auto"
                >
                  查看作者页
                </button>
              </div>
            )}

        <UserHeaderCard
          user={user}
          subtitle="个人中心：统一管理我的书单、关注、创建内容与偏好设置。"
        />

        <UserStatsGrid items={stats} />

            <div className="flex flex-col items-center gap-4 text-center">
              <div className="flex flex-wrap items-center justify-center gap-2">
          {tabOptions.map((item) => {
            const Icon = item.icon;
            const active = tab === item.key;
            return (
              <button
                key={item.key}
                  type="button"
                  onClick={() => setTab(item.key)}
                  className={`od-pill-chip inline-flex items-center gap-1.5 text-xs transition-colors ${
                    active
                      ? 'bg-[var(--od-accent)] text-white font-od-bold'
                      : 'text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)] font-od-medium'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                {item.label}
              </button>
            );
          })}

        </div>
              <p className="text-sm leading-6 text-[var(--od-text-secondary)]">
                在这里切换你的书单、关注、创建内容和搜索偏好，信息按分段展开，不再堆叠成后台式面板。
              </p>
            </div>
          </div>
        </section>

        {tab === 'booklists' && (
          <section className="px-1">
            <FluidDivider label="Booklists" className="mb-8" />
            <div className="mb-6 flex flex-col items-center gap-3 text-center">
              <div className="flex items-center gap-2 justify-center">
                <BookOpen className="h-4 w-4 text-[var(--od-accent)]" />
                <h2 className="od-text-title">我的书单</h2>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateBooklist(true)}
                className="od-inline-action od-inline-action-primary w-full justify-center sm:w-auto"
              >
                新建书单
              </button>
            </div>

            <div className="mb-6 flex flex-wrap items-center justify-center gap-2">
              <button
                type="button"
                onClick={() => setBooklistSubTab('mine')}
                className={`od-pill-chip text-xs ${
                  booklistSubTab === 'mine'
                    ? 'bg-[var(--od-accent)] text-white font-od-bold'
                    : 'text-[var(--od-text-secondary)] font-od-medium'
                }`}
              >
                我的创建
              </button>
              <button
                type="button"
                onClick={() => setBooklistSubTab('collected')}
                className={`od-pill-chip text-xs ${
                  booklistSubTab === 'collected'
                    ? 'bg-[var(--od-accent)] text-white font-od-bold'
                    : 'text-[var(--od-text-secondary)] font-od-medium'
                }`}
              >
                我的收藏
              </button>
              <button
                type="button"
                onClick={() => {
                  void myBooklistsQuery.refetch();
                  void collectedBooklistsQuery.refetch();
                }}
                className="od-inline-action od-inline-action-ghost"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>
            </div>

            {(myBooklistsQuery.isLoading || collectedBooklistsQuery.isLoading) ? (
              <p className="od-text-body">加载书单中...</p>
            ) : activeBooklists.length === 0 ? (
              <p className="od-text-body">当前分组暂无数据。</p>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {activeBooklists.map((booklist) => (
                  <BooklistCard
                    key={booklist.id}
                    booklist={booklist}
                    canManage={String(booklist.owner_id) === String(user?.id)}
                    onOpen={(id) => navigate(`/booklists/${id}`)}
                    onToggleCollect={(item) =>
                      collectMutation.mutate({ id: item.id, collected: Boolean(item.collected_flag) })
                    }
                    onEdit={(item) => setEditingBooklist(item)}
                    onDelete={(item) => {
                      if (!window.confirm(`确认删除书单「${item.title}」？`)) return;
                      deleteMutation.mutate(item.id);
                    }}
                    collectLoading={collectMutation.isPending}
                  />
                ))}
              </div>
            )}
          </section>
        )}

        {tab === 'follows' && (
          <section className="px-1">
            <FluidDivider label="Follows" className="mb-8" />
            <div className="mb-6 flex flex-col items-center gap-3 text-center">
              <div className="flex items-center justify-center gap-2">
                <Bookmark className="h-4 w-4 text-[var(--od-accent)]" />
                <h2 className="od-text-title">我的关注</h2>
              </div>
              <button
                type="button"
                onClick={() => void followsQuery.refetch()}
                className="od-inline-action od-inline-action-ghost"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>
            </div>

            {followsQuery.isLoading ? (
              <p className="od-text-body">加载关注中...</p>
            ) : followsQuery.isError ? (
              <p className="od-text-body text-[var(--od-text-emphasis)]">关注列表加载失败。</p>
            ) : (followsQuery.data?.results?.length || 0) === 0 ? (
              <p className="od-text-body">暂无关注内容。</p>
            ) : (
              <ThreadResultsCollection threads={followsQuery.data?.results || []} onPreview={openPreview} />
            )}
          </section>
        )}

        {tab === 'threads' && (
          <section className="px-1">
            <FluidDivider label="Threads" className="mb-8" />
            <div className="mb-6 flex flex-col items-center gap-3 text-center">
              <div className="flex items-center justify-center gap-2">
                <FileText className="h-4 w-4 text-[var(--od-accent)]" />
                <h2 className="od-text-title">我的创建</h2>
              </div>
              <button
                type="button"
                onClick={() => void createdThreadsQuery.refetch()}
                className="od-inline-action od-inline-action-ghost"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>
            </div>

            <div className="mb-8 mx-auto grid max-w-4xl grid-cols-2 gap-x-6 gap-y-5 text-center sm:grid-cols-4">
              <div>
                <p className="text-sm font-medium text-[var(--od-text-secondary)]">帖子数</p>
                <p className="mt-2 text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-value)] tabular-nums">
                  {createdThreadsQuery.data?.total || 0}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-[var(--od-text-secondary)]">累计点赞</p>
                <p className="mt-2 text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-value)] tabular-nums">
                  {totalReactions}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-[var(--od-text-secondary)]">累计回复</p>
                <p className="mt-2 text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-value)] tabular-nums">
                  {totalReplies}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-[var(--od-text-secondary)]">当前加载</p>
                <p className="mt-2 text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-value)] tabular-nums">
                  {createdThreads.length}
                </p>
              </div>
            </div>

            {createdThreadsQuery.isLoading ? (
              <p className="od-text-body">加载创建内容中...</p>
            ) : createdThreads.length === 0 ? (
              <p className="od-text-body">还没有检索到你的创建内容。</p>
            ) : (
              <ThreadResultsCollection threads={createdThreads} onPreview={openPreview} />
            )}
          </section>
        )}

        {tab === 'preferences' && (
          <section className="px-1">
            <FluidDivider label="Preferences" className="mb-8" />
            <div className="mb-6 flex items-center justify-center gap-2 text-center">
              <Search className="h-4 w-4 text-[var(--od-accent)]" />
              <h2 className="od-text-title">发现偏好</h2>
            </div>

            {isPrefsLoading ? (
              <p className="od-text-body">加载偏好中...</p>
            ) : (
              <div className="space-y-8">
                <div className="space-y-3">
                  <p className="text-sm font-medium text-[var(--od-text-primary)]">偏好频道</p>
                  <p className="text-sm leading-6 text-[var(--od-text-secondary)]">
                    这些频道会在空搜索探索和搜索建议里优先生效，作为你个人展示层过滤的起点；一旦你手动点频道或输入搜索词，它们就会让位给你的当前意图。
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {channelOptions.map((channel) => {
                      const active = form.preferredChannelIds.includes(channel.id);
                      return (
                        <button
                          key={channel.id}
                          type="button"
                          onClick={() => toggleChannel(channel.id)}
                          className={`rounded-2xl border px-4 py-3 text-left text-sm transition-colors ${
                            active
                              ? 'border-[var(--od-accent)]/40 bg-[var(--od-accent)]/8 text-[var(--od-text-primary)] font-od-medium'
                              : 'border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] text-[var(--od-text-secondary)] font-od-normal'
                          }`}
                        >
                          {channel.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid gap-6 sm:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="block text-sm font-medium text-[var(--od-text-secondary)]">默认排序</span>
                    <select
                      value={form.sortMethod}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, sortMethod: e.target.value as PreferencesFormValue['sortMethod'] }));
                      }}
                      className="w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4 py-3 text-sm text-[var(--od-text-primary)]"
                    >
                      <option value="last_active_desc">最后活跃</option>
                      <option value="created_desc">最新发布</option>
                      <option value="reaction_desc">点赞热度</option>
                      <option value="reply_desc">讨论热度</option>
                      <option value="relevance">综合推荐</option>
                    </select>
                  </label>

                  <label className="block space-y-2">
                    <span className="block text-sm font-medium text-[var(--od-text-secondary)]">每页条数</span>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={form.resultsPerPage}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, resultsPerPage: Number(e.target.value) || 24 }));
                      }}
                      className="w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4 py-3 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>
                </div>

                <div className="grid gap-6 sm:grid-cols-2">
                  <PreferenceTagSelector
                    label="包含标签"
                    placeholder="还没有设置正选标签"
                    selectedTags={form.includeTagsText.split(',').map((item) => item.trim()).filter(Boolean)}
                    availableTags={availablePreferenceTags.filter((tag) => !form.excludeTagsText.split(',').map((item) => item.trim()).filter(Boolean).includes(tag))}
                    tone="include"
                    onChange={(tags) => {
                      setIsDirty(true);
                      setForm((prev) => ({ ...prev, includeTagsText: tags.join(', ') }));
                    }}
                  />
                  <PreferenceTagSelector
                    label="排除标签"
                    placeholder="还没有设置反选标签"
                    selectedTags={form.excludeTagsText.split(',').map((item) => item.trim()).filter(Boolean)}
                    availableTags={availablePreferenceTags.filter((tag) => !form.includeTagsText.split(',').map((item) => item.trim()).filter(Boolean).includes(tag))}
                    tone="exclude"
                    onChange={(tags) => {
                      setIsDirty(true);
                      setForm((prev) => ({ ...prev, excludeTagsText: tags.join(', ') }));
                    }}
                  />
                </div>

                <div className="grid gap-6 sm:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="block text-sm font-medium text-[var(--od-text-secondary)]">关键词包含</span>
                    <textarea
                      value={form.includeKeywordsText}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, includeKeywordsText: e.target.value }));
                      }}
                      className="min-h-[110px] w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4 py-3 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>
                  <label className="block space-y-2">
                    <span className="block text-sm font-medium text-[var(--od-text-secondary)]">关键词排除</span>
                    <textarea
                      value={form.excludeKeywordsText}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, excludeKeywordsText: e.target.value }));
                      }}
                      className="min-h-[110px] w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4 py-3 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>
                </div>

                <div className="rounded-[1.2rem] border border-[color-mix(in_srgb,var(--od-text-secondary)_14%,transparent)] bg-[color-mix(in_srgb,var(--od-surface-input)_56%,transparent)] px-4 py-4 text-sm leading-6 text-[var(--od-text-secondary)]">
                  这些偏好现在主要作用于“发现流”而不是搜索框本身：空搜索状态的展示页、全频道探索态与搜索建议会参考它们，但不会把它们偷偷写进你的输入框，也不会压过你手动选择的频道。
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[color-mix(in_srgb,var(--od-text-secondary)_14%,transparent)] pt-5">
                  <p className="od-text-meta">
                    当前状态：{isPrefsFetching ? '同步中' : isDirty ? '有未保存修改' : '已同步'}
                  </p>
                  <button
                    type="button"
                    onClick={savePreferenceForm}
                    disabled={isSaving}
                    className="od-inline-action od-inline-action-primary disabled:opacity-60"
                  >
                    <Save className="h-4 w-4" />
                    {isSaving ? '保存中...' : '保存偏好'}
                  </button>
                </div>
              </div>
            )}
          </section>
        )}
      </div>

      <BooklistFormModal
        isOpen={showCreateBooklist}
        submitting={createMutation.isPending}
        onClose={() => setShowCreateBooklist(false)}
        onSubmit={(payload) => createMutation.mutate(payload)}
      />

      <BooklistFormModal
        isOpen={Boolean(editingBooklist)}
        initialValue={editingBooklist || undefined}
        submitting={updateMutation.isPending}
        onClose={() => setEditingBooklist(null)}
        onSubmit={(payload) => {
          if (!editingBooklist) return;
          updateMutation.mutate({ id: editingBooklist.id, payload });
        }}
      />

    </>
  );
}
