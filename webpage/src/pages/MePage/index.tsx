import { useEffect, useMemo, useState, type ComponentType } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Bookmark, FileText, RefreshCw, Save, Search, Settings2 } from 'lucide-react';
import { toast } from 'sonner';

import { UserHeaderCard } from '@/entities/user/UserHeaderCard';
import { UserStatsGrid } from '@/entities/user/UserStatsGrid';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useSettings } from '@/shared/hooks/useSettings';
import { ThreadCard } from '@/entities/thread/ThreadCard';
import { ThreadListItem } from '@/entities/thread/ThreadListItem';
import type { Thread } from '@/entities/thread/types';
import { ThreadPreviewOverlay } from '@/widgets/thread-preview/ThreadPreviewOverlay';
import { followsApi } from '@/features/follows/api/followsApi';
import { searchApi } from '@/features/search/api/searchApi';
import { BooklistCard } from '@/entities/booklist/BooklistCard';
import type { Booklist, BooklistFormInput } from '@/entities/booklist/types';
import { booklistsApi } from '@/features/booklists/api/booklistsApi';
import { BooklistFormModal } from '@/features/booklists/components/BooklistFormModal';
import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
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
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { settings } = useSettings();
  const { user } = useAuth();

  const tab = parseTab(searchParams.get('tab'));
  const booklistSubTab = parseBooklistSubTab(searchParams.get('booklists'));

  const [previewThread, setPreviewThread] = useState<Thread | null>(null);
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

  const followsQuery = useQuery({
    queryKey: ['me', 'follows'],
    queryFn: followsApi.getFollows,
    staleTime: 60 * 1000,
  });

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

  const myBooklistsQuery = useQuery({
    queryKey: ['me', 'booklists', 'mine'],
    queryFn: () =>
      booklistsApi.listMine({
        createByCurrentUser: true,
        pageIndex: 0,
        pageSize: 18,
        sortMethod: 5,
      }),
    staleTime: 60 * 1000,
  });

  const collectedBooklistsQuery = useQuery({
    queryKey: ['me', 'booklists', 'collected'],
    queryFn: () =>
      booklistsApi.listMine({
        collectByCurrentUser: true,
        pageIndex: 0,
        pageSize: 18,
        sortMethod: 6,
      }),
    staleTime: 60 * 1000,
  });

  const collectMutation = useMutation({
    mutationFn: ({ id, collected }: { id: number; collected: boolean }) =>
      collected ? booklistsApi.uncollect([id]) : booklistsApi.collect([id]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'booklists'] });
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
      queryClient.invalidateQueries({ queryKey: ['booklist-detail'] });
    },
    onError: () => toast.error('收藏状态更新失败'),
  });

  const createMutation = useMutation({
    mutationFn: (payload: BooklistFormInput) => booklistsApi.create(payload),
    onSuccess: () => {
      toast.success('书单创建成功');
      setShowCreateBooklist(false);
      queryClient.invalidateQueries({ queryKey: ['me', 'booklists'] });
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
    },
    onError: () => toast.error('书单创建失败'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: BooklistFormInput }) => booklistsApi.update(id, payload),
    onSuccess: () => {
      toast.success('书单已更新');
      setEditingBooklist(null);
      queryClient.invalidateQueries({ queryKey: ['me', 'booklists'] });
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
    },
    onError: () => toast.error('更新失败'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => booklistsApi.remove(id),
    onSuccess: () => {
      toast.success('书单已删除');
      queryClient.invalidateQueries({ queryKey: ['me', 'booklists'] });
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
    },
    onError: () => toast.error('删除失败'),
  });

  const createdThreads = (createdThreadsQuery.data?.results || []) as Thread[];
  const totalReactions = createdThreads.reduce((sum, item) => sum + (Number(item.reaction_count) || 0), 0);
  const totalReplies = createdThreads.reduce((sum, item) => sum + (Number(item.reply_count) || 0), 0);
  const totalFollows = followsQuery.data?.total || 0;
  const totalBooklists = myBooklistsQuery.data?.total || 0;

  const stats = [
    { label: '我的书单', value: totalBooklists },
    { label: '我的关注', value: totalFollows },
    { label: '我的帖子', value: createdThreadsQuery.data?.total || 0 },
    { label: '累计点赞', value: totalReactions },
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
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
        <UserHeaderCard
          user={user}
          subtitle="个人中心：统一管理我的书单、关注、创建内容与偏好设置。"
        />

        <UserStatsGrid items={stats} />

        <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-3">
          {tabOptions.map((item) => {
            const Icon = item.icon;
            const active = tab === item.key;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => setTab(item.key)}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                  active
                    ? 'bg-[var(--od-accent)] text-white'
                    : 'bg-[var(--od-bg-secondary)] text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </button>
            );
          })}

          {user?.id && (
            <button
              type="button"
              onClick={() => navigate(`/u/${user.id}`)}
              className="ml-auto rounded-md border border-[var(--od-border)] px-3 py-1.5 text-xs text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]"
            >
              查看作者页
            </button>
          )}
        </div>

        {tab === 'booklists' && (
          <section className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 sm:p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-[var(--od-accent)]" />
                <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">我的书单</h2>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateBooklist(true)}
                className="rounded-md bg-[var(--od-accent)] px-3 py-1.5 text-xs font-semibold text-white"
              >
                新建书单
              </button>
            </div>

            <div className="mb-4 flex items-center gap-2">
              <button
                type="button"
                onClick={() => setBooklistSubTab('mine')}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                  booklistSubTab === 'mine'
                    ? 'bg-[var(--od-accent)] text-white'
                    : 'bg-[var(--od-bg-secondary)] text-[var(--od-text-secondary)]'
                }`}
              >
                我的创建
              </button>
              <button
                type="button"
                onClick={() => setBooklistSubTab('collected')}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                  booklistSubTab === 'collected'
                    ? 'bg-[var(--od-accent)] text-white'
                    : 'bg-[var(--od-bg-secondary)] text-[var(--od-text-secondary)]'
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
                className="ml-auto inline-flex items-center gap-1 rounded-md border border-[var(--od-border)] px-2.5 py-1 text-xs text-[var(--od-text-secondary)]"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>
            </div>

            {(myBooklistsQuery.isLoading || collectedBooklistsQuery.isLoading) ? (
              <p className="text-sm text-[var(--od-text-secondary)]">加载书单中...</p>
            ) : activeBooklists.length === 0 ? (
              <p className="text-sm text-[var(--od-text-secondary)]">当前分组暂无数据。</p>
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
          <section className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 sm:p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Bookmark className="h-4 w-4 text-[var(--od-accent)]" />
                <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">我的关注</h2>
              </div>
              <button
                type="button"
                onClick={() => void followsQuery.refetch()}
                className="inline-flex items-center gap-1 rounded-md border border-[var(--od-border)] px-2.5 py-1 text-xs text-[var(--od-text-secondary)]"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>
            </div>

            {followsQuery.isLoading ? (
              <p className="text-sm text-[var(--od-text-secondary)]">加载关注中...</p>
            ) : followsQuery.isError ? (
              <p className="text-sm text-[var(--od-error)]">关注列表加载失败。</p>
            ) : (followsQuery.data?.results?.length || 0) === 0 ? (
              <p className="text-sm text-[var(--od-text-secondary)]">暂无关注内容。</p>
            ) : (
              <div className={settings.layoutMode === 'list' ? 'flex flex-col space-y-od-list-gap' : 'grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'}>
                {(followsQuery.data?.results || []).map((thread) =>
                  settings.layoutMode === 'list' ? (
                    <ThreadListItem key={thread.thread_id} thread={thread} onPreview={setPreviewThread} />
                  ) : (
                    <ThreadCard key={thread.thread_id} thread={thread} onPreview={setPreviewThread} />
                  ),
                )}
              </div>
            )}
          </section>
        )}

        {tab === 'threads' && (
          <section className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 sm:p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-[var(--od-accent)]" />
                <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">我的创建</h2>
              </div>
              <button
                type="button"
                onClick={() => void createdThreadsQuery.refetch()}
                className="inline-flex items-center gap-1 rounded-md border border-[var(--od-border)] px-2.5 py-1 text-xs text-[var(--od-text-secondary)]"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>
            </div>

            <div className="mb-4 grid grid-cols-2 gap-2 rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] p-3 text-xs text-[var(--od-text-secondary)] sm:grid-cols-4">
              <span>帖子数：{createdThreadsQuery.data?.total || 0}</span>
              <span>累计点赞：{totalReactions}</span>
              <span>累计回复：{totalReplies}</span>
              <span>当前加载：{createdThreads.length}</span>
            </div>

            {createdThreadsQuery.isLoading ? (
              <p className="text-sm text-[var(--od-text-secondary)]">加载创建内容中...</p>
            ) : createdThreads.length === 0 ? (
              <p className="text-sm text-[var(--od-text-secondary)]">还没有检索到你的创建内容。</p>
            ) : (
              <div className={settings.layoutMode === 'list' ? 'flex flex-col space-y-od-list-gap' : 'grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'}>
                {createdThreads.map((thread) =>
                  settings.layoutMode === 'list' ? (
                    <ThreadListItem key={thread.thread_id} thread={thread} onPreview={setPreviewThread} />
                  ) : (
                    <ThreadCard key={thread.thread_id} thread={thread} onPreview={setPreviewThread} />
                  ),
                )}
              </div>
            )}
          </section>
        )}

        {tab === 'preferences' && (
          <section className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 sm:p-5">
            <div className="mb-4 flex items-center gap-2">
              <Search className="h-4 w-4 text-[var(--od-accent)]" />
              <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">搜索偏好</h2>
            </div>

            {isPrefsLoading ? (
              <p className="text-sm text-[var(--od-text-secondary)]">加载偏好中...</p>
            ) : (
              <div className="space-y-5">
                <div>
                  <p className="mb-2 text-sm font-medium text-[var(--od-text-secondary)]">偏好频道</p>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {channelOptions.map((channel) => {
                      const active = form.preferredChannelIds.includes(channel.id);
                      return (
                        <button
                          key={channel.id}
                          type="button"
                          onClick={() => toggleChannel(channel.id)}
                          className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                            active
                              ? 'border-[var(--od-accent)] bg-[var(--od-accent)]/10 text-[var(--od-text-primary)]'
                              : 'border-[var(--od-border)] bg-[var(--od-bg-secondary)] text-[var(--od-text-secondary)]'
                          }`}
                        >
                          {channel.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">默认排序</span>
                    <select
                      value={form.sortMethod}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, sortMethod: e.target.value as PreferencesFormValue['sortMethod'] }));
                      }}
                      className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    >
                      <option value="last_active_desc">最后活跃</option>
                      <option value="created_desc">最新发布</option>
                      <option value="reaction_desc">点赞热度</option>
                      <option value="reply_desc">讨论热度</option>
                      <option value="relevance">综合推荐</option>
                    </select>
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">每页条数</span>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={form.resultsPerPage}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, resultsPerPage: Number(e.target.value) || 24 }));
                      }}
                      className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">包含标签（逗号分隔）</span>
                    <input
                      type="text"
                      value={form.includeTagsText}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, includeTagsText: e.target.value }));
                      }}
                      className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">排除标签（逗号分隔）</span>
                    <input
                      type="text"
                      value={form.excludeTagsText}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, excludeTagsText: e.target.value }));
                      }}
                      className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">关键词包含</span>
                    <textarea
                      value={form.includeKeywordsText}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, includeKeywordsText: e.target.value }));
                      }}
                      className="min-h-[88px] w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">关键词排除</span>
                    <textarea
                      value={form.excludeKeywordsText}
                      onChange={(e) => {
                        setIsDirty(true);
                        setForm((prev) => ({ ...prev, excludeKeywordsText: e.target.value }));
                      }}
                      className="min-h-[88px] w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--od-border)] bg-[var(--od-bg-secondary)] p-3">
                  <p className="text-xs text-[var(--od-text-tertiary)]">
                    当前状态：{isPrefsFetching ? '同步中' : isDirty ? '有未保存修改' : '已同步'}
                  </p>
                  <button
                    type="button"
                    onClick={savePreferenceForm}
                    disabled={isSaving}
                    className="inline-flex items-center gap-2 rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
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

      {previewThread && (
        <ThreadPreviewOverlay thread={previewThread} onClose={() => setPreviewThread(null)} />
      )}
    </>
  );
}
