import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bookmark } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { ThreadCard } from '@/features/threads/components/ThreadCard';
import { ThreadCardSkeleton } from '@/features/threads/components/ThreadCardSkeleton';
import { followsApi } from '@/features/follows/api/followsApi';
import { useSettings } from '@/hooks/useSettings';
import { ThreadPreviewOverlay } from '@/features/threads/components/ThreadPreviewOverlay';
import { useSearchStore } from '@/features/search/store/searchStore';
import { apiClient } from '@/lib/api/client';
import type { Thread, Channel } from '@/types/thread.types';

export function FollowsPage() {
  const { selectedChannel } = useSearchStore();

  // 获取频道列表以显示频道名称
  const { data: channels } = useQuery({
    queryKey: ['meta', 'channels'],
    queryFn: async () => {
      const res = await apiClient.get<Channel[]>('/meta/channels');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  // 使用真实API获取关注列表
  const { data: followsData, isLoading } = useQuery({
    queryKey: ['follows'],
    queryFn: followsApi.getFollows,
    staleTime: 60 * 1000, // 1分钟
  });

  const allFollows = followsData?.results || [];
  const unreadCount = followsData?.unread_count || 0;

  // 根据选中的频道筛选关注列表
  const follows = useMemo(() => {
    if (!selectedChannel) return allFollows;
    return allFollows.filter(thread => thread.channel_id === selectedChannel);
  }, [allFollows, selectedChannel]);

  // 获取当前频道名称
  const currentChannelName = useMemo(() => {
    if (!selectedChannel || !channels) return null;
    const channel = channels.find(ch => ch.id === selectedChannel);
    return channel?.name;
  }, [selectedChannel, channels]);
  const { settings } = useSettings();
  const [previewThread, setPreviewThread] = useState<Thread | null>(null);

  const handleClosePreview = () => {
    setPreviewThread(null);
  };

  return (
    <MainLayout>
      <div>
        {/* 标题栏 */}
        <div className="border-b border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bookmark className="h-6 w-6 text-[#f2f3f5]" />
              <div>
                <h1 className="text-xl font-bold text-[var(--od-text-primary)]">
                  我的关注{currentChannelName && ` · ${currentChannelName}`}
                </h1>
                <p className="text-sm text-[var(--od-text-secondary)]">
                  共 {follows.length} 个帖子
                  {selectedChannel && allFollows.length !== follows.length && (
                    <span className="ml-2 text-xs text-[var(--od-text-tertiary)]">
                      （全部 {allFollows.length} 个）
                    </span>
                  )}
                  {unreadCount > 0 && (
                    <span className="ml-2 rounded bg-[#23a55a] px-2 py-0.5 text-xs font-bold text-white">
                      {unreadCount} 个更新
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* 关注列表 */}
        <div className="p-4">
          {isLoading ? (
            <div className={`grid grid-cols-1 gap-4 sm:grid-cols-2 ${settings.sidebarCollapsed ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}>
              {Array.from({ length: 6 }).map((_, i) => (
                <ThreadCardSkeleton key={i} />
              ))}
            </div>
          ) : follows.length > 0 ? (
            <div className={`grid grid-cols-1 gap-4 sm:grid-cols-2 ${settings.sidebarCollapsed ? 'lg:grid-cols-4' : 'lg:grid-cols-3'} animate-in fade-in duration-500`}>
              {follows.map((thread, index) => (
                <div
                  key={thread.id}
                  className="animate-in fade-in slide-in-from-bottom-4"
                  style={{
                    animationDelay: `${index * 50}ms`,
                    animationFillMode: 'backwards',
                  }}
                >
                  <ThreadCard thread={thread} onPreview={setPreviewThread} />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex min-h-[400px] items-center justify-center">
              <div className="text-center">
                <Bookmark className="mx-auto mb-4 h-16 w-16 text-[var(--od-border-strong)]" />
                <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">
                  还没有关注任何帖子
                </h3>
                <p className="text-[var(--od-text-secondary)]">
                  在Discord中使用Bot命令关注帖子
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {previewThread && (
        <ThreadPreviewOverlay thread={previewThread} onClose={handleClosePreview} />
      )}
    </MainLayout>
  );
}
