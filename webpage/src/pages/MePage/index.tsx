import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Bookmark, Eye, FileText, Heart, Settings2 } from 'lucide-react';

import { useAuth } from '@/features/auth/hooks/useAuth';
import type { Thread } from '@/entities/thread/types';
import { useFollowsFeed } from '@/features/follows/hooks/useFollowsData';
import { searchApi } from '@/features/search/api/searchApi';
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
import { FluidDivider } from '@/shared/ui/FluidDivider';
import {
  toPreferencesFormValue,
  toPreferencesUpdatePayload,
  type PreferencesFormValue,
} from '@/features/preferences/lib/preferencesMapper';
import { MeBooklistsSection, type BooklistSubTab } from '@/pages/MePage/MeBooklistsSection';
import { MeFollowsSection } from '@/pages/MePage/MeFollowsSection';
import { MeHistorySection } from '@/pages/MePage/MeHistorySection';
import { MePageHeader, type MePageTabOption } from '@/pages/MePage/MePageHeader';
import { MePreferencesSection } from '@/pages/MePage/MePreferencesSection';
import { MeThreadsSection } from '@/pages/MePage/MeThreadsSection';
import { useChannels } from '@/shared/hooks/useChannels';
import { GUILD_ID } from '@/shared/config/channelCategories.private';
import { clearBrowseHistory, getBrowseHistory, removeBrowseHistory } from '@/shared/lib/browseHistory';
import { notifyError, notifySuccess } from '@/shared/lib/notify';

type MeTab = 'booklists' | 'follows' | 'threads' | 'history' | 'preferences';

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

const tabOptions: MePageTabOption[] = [
  { key: 'booklists', label: '书单', icon: BookOpen },
  { key: 'follows', label: '关注', icon: Bookmark },
  { key: 'threads', label: '创建', icon: FileText },
  { key: 'history', label: '足迹', icon: Eye },
  { key: 'preferences', label: '偏好', icon: Settings2 },
];

function parseTab(value: string | null): MeTab {
  if (value === 'booklists' || value === 'follows' || value === 'threads' || value === 'history' || value === 'preferences') {
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
  const { openPreview, openPreviewById } = usePreviewThread();

  const tab = parseTab(searchParams.get('tab'));
  const booklistSubTab = parseBooklistSubTab(searchParams.get('booklists'));

  const [showCreateBooklist, setShowCreateBooklist] = useState(false);
  const [editingBooklist, setEditingBooklist] = useState<Booklist | null>(null);
  const [browseHistoryVersion, setBrowseHistoryVersion] = useState(0);

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

  useEffect(() => {
    if (tab === 'history') {
      // Allow DOM to update first
      setTimeout(() => {
        document.getElementById('history-section')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  }, [tab]);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key && event.key !== 'odysseia_browse_history') return;
      setBrowseHistoryVersion((value) => value + 1);
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const { data: channelsData } = useChannels();
  const channelOptions = useMemo(() => channelsData?.channels || [], [channelsData?.channels]);
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
  const browseHistory = useMemo(() => getBrowseHistory(), [browseHistoryVersion]);
  const followedThreads = useMemo(() => {
    const threads = followsQuery.data?.results || [];
    const selectedFollowChannel = searchParams.get('channel');
    if (!selectedFollowChannel) return threads;
    return threads.filter((thread) => String(thread.channel_id) === String(selectedFollowChannel));
  }, [followsQuery.data?.results, searchParams]);
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
      notifySuccess('偏好已保存');
    } catch {
      notifyError('保存偏好失败');
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
          <MePageHeader
            currentTab={tab}
            onOpenProfile={() => navigate(`/u/${user!.id}`)}
            onSelectTab={(nextTab) => setTab(nextTab as MeTab)}
            showProfileButton={Boolean(user?.id)}
            stats={stats}
            tabOptions={tabOptions}
            user={user}
          />
        </section>

        {tab === 'booklists' && (
          <MeBooklistsSection
            activeBooklists={activeBooklists}
            collectLoading={collectMutation.isPending}
            isLoading={myBooklistsQuery.isLoading || collectedBooklistsQuery.isLoading}
            subTab={booklistSubTab}
            userId={user?.id}
            onCreate={() => setShowCreateBooklist(true)}
            onDelete={(item) => {
              if (!window.confirm(`确认删除书单「${item.title}」？`)) return;
              deleteMutation.mutate(item.id);
            }}
            onEdit={(item) => setEditingBooklist(item)}
            onOpen={(id) => navigate(`/booklists/${id}`)}
            onRefresh={() => {
              void myBooklistsQuery.refetch();
              void collectedBooklistsQuery.refetch();
            }}
            onSetSubTab={setBooklistSubTab}
            onToggleCollect={(item) => {
              collectMutation.mutate({ id: item.id, collected: Boolean(item.collected_flag) });
            }}
          />
        )}

        {tab === 'follows' && (
          <MeFollowsSection
            hasAnyResults={(followsQuery.data?.results?.length || 0) > 0}
            isError={followsQuery.isError}
            isLoading={followsQuery.isLoading}
            selectedChannel={searchParams.get('channel')}
            threads={followedThreads}
            onClearChannel={() => {
              const nextParams = new URLSearchParams(searchParams);
              nextParams.delete('channel');
              setSearchParams(nextParams, { replace: true });
            }}
            onPreview={openPreview}
            onRefresh={() => void followsQuery.refetch()}
          />
        )}

        {tab === 'threads' && (
          <MeThreadsSection
            isLoading={createdThreadsQuery.isLoading}
            threads={createdThreads}
            totalReplies={totalReplies}
            totalReactions={totalReactions}
            totalThreads={createdThreadsQuery.data?.total || 0}
            onPreview={openPreview}
            onRefresh={() => void createdThreadsQuery.refetch()}
          />
        )}

        {tab === 'history' && (
          <MeHistorySection
            historyItems={browseHistory}
            onClear={() => {
              clearBrowseHistory();
              setBrowseHistoryVersion((value) => value + 1);
            }}
            onOpenThread={openPreviewById}
            onRefresh={() => setBrowseHistoryVersion((value) => value + 1)}
            onRemove={(threadId) => {
              removeBrowseHistory(threadId);
              setBrowseHistoryVersion((value) => value + 1);
            }}
          />
        )}

        {tab === 'preferences' && (
          <MePreferencesSection
            availablePreferenceTags={availablePreferenceTags}
            channelOptions={channelOptions}
            form={form}
            isDirty={isDirty}
            isLoading={isPrefsLoading}
            isSaving={isSaving}
            isSyncing={isPrefsFetching}
            onSave={savePreferenceForm}
            onToggleChannel={toggleChannel}
            onUpdateForm={(updater) => {
              setIsDirty(true);
              setForm((prev) => updater(prev));
            }}
          />
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
