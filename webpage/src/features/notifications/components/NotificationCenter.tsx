import { Bell, X, AlertCircle, Trash2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { followsApi } from '@/features/follows/api/followsApi';
import type { Thread } from '@/entities/thread/types';
import { APP_VERSION } from '@/shared/config/appInfo';
import { resolveStaticNotifications } from '@/features/notifications/notificationsConfig';
import { usePreviewStore } from '@/features/search/store/previewStore';

type NotificationKind = 'follow_update' | 'release_update';

interface NotificationItem {
  id: string;
  kind: NotificationKind;
  title: string;
  message: string;
  created_at?: string;
  thread?: Thread;
  source?: 'webpage' | 'system';
}

interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
  onUnreadChange?: (count: number) => void;
}

export function NotificationCenter({ open, onClose, onUnreadChange }: NotificationCenterProps) {
  const navigate = useNavigate();

  const setPreviewThread = usePreviewStore((state) => state.setPreviewThread);

  // 本地持久化：已关闭的静态通知（站点公告 / 问候语）
  const [dismissedStaticIds, setDismissedStaticIds] = useState<string[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const raw = window.localStorage.getItem('od_notifications_dismissed');
      return raw ? (JSON.parse(raw) as string[]) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem('od_notifications_dismissed', JSON.stringify(dismissedStaticIds));
    } catch {
      // ignore
    }
  }, [dismissedStaticIds]);

  const [dismissedFollowUpdates, setDismissedFollowUpdates] = useState<Record<string, string>>({});

  const { data, isLoading, isError } = useQuery({
    queryKey: ['follows'],
    queryFn: followsApi.getFollows,
    staleTime: 60 * 1000,
    refetchInterval: 30 * 1000,
    refetchOnWindowFocus: true,
  });

  const {
    data: staticDefs = [],
    isLoading: isStaticLoading,
    isError: isStaticError,
  } = useQuery({
    queryKey: ['release-notifications', APP_VERSION],
    queryFn: () => resolveStaticNotifications({ currentAppVersion: APP_VERSION }),
    staleTime: 5 * 60 * 1000,
  });

  const follows = data?.results ?? [];
  const unreadCount = data?.unread_count ?? 0;

  // 版本 / 系统更新通知（可永久关闭）
  const staticNotifications: NotificationItem[] = staticDefs
    .filter((def) => !dismissedStaticIds.includes(def.id))
    .map((def) => ({
      id: def.id,
      kind: def.kind,
      title: def.title,
      message: def.message,
      created_at: def.created_at,
      thread: def.previewThread,
      source: def.source,
    }));

  // 关注更新类通知
  const followNotifications: NotificationItem[] = follows
    .filter((thread) => thread.has_update)
    .filter((thread) => {
      const id = `follow-${thread.thread_id}`;
      const currentUpdateStamp = thread.last_active_at ?? thread.created_at;
      const dismissedStamp = dismissedFollowUpdates[id];
      return dismissedStamp !== currentUpdateStamp;
    })
    .map((thread) => ({
      id: `follow-${thread.thread_id}`,
      kind: 'follow_update' as const,
      title: thread.title,
      message: thread.first_message_excerpt ?? '该帖子有新的更新。',
      created_at: thread.last_active_at ?? undefined,
      thread,
    }));

  const allNotifications: NotificationItem[] = [...staticNotifications, ...followNotifications];
  const hasAnyNotification = allNotifications.length > 0;
  const effectiveUnreadCount = unreadCount;
  const unreadTotal = allNotifications.length;

  // 将当前未读通知数量回传给父级（用于侧边栏铃铛动画和红点）
  useEffect(() => {
    onUnreadChange?.(unreadTotal);
  }, [unreadTotal, onUnreadChange]);

  const handleNotificationClick = (item: NotificationItem) => {
    // 关注帖子更新：点击即视为已读，从列表中移除，并打开详情预览
    if (item.kind === 'follow_update' && item.thread) {
      const currentUpdateStamp = item.thread.last_active_at ?? item.thread.created_at;
      setDismissedFollowUpdates((prev) => ({
        ...prev,
        [item.id]: currentUpdateStamp,
      }));

      setPreviewThread(item.thread);
      return;
    }

    // 更新公告：点击后也视为已读，并复用详情预览浮层
    setDismissedStaticIds((prev) => (prev.includes(item.id) ? prev : [...prev, item.id]));

    setPreviewThread(item.thread ?? null, {
      hideExternalButton: true,
      externalUrlOverride: null,
    });
  };

  const handleDismissStatic = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDismissedStaticIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
  };

  const queryClient = useQueryClient();

  const handleClearAllNotifications = async () => {
    // 更新通知：全部标记为已关闭
    setDismissedStaticIds((prev) => {
      const allStaticIds = staticDefs.map((d) => d.id);
      const merged = Array.from(new Set([...prev, ...allStaticIds]));
      return merged;
    });

    // 关注帖子通知：基于当前 has_update 的帖子全部标记为已读
    setDismissedFollowUpdates((prev) => {
      const next = { ...prev };
      for (const thread of follows) {
        if (!thread.has_update) continue;
        const id = `follow-${thread.thread_id}`;
        next[id] = thread.last_active_at ?? thread.created_at;
      }
      return next;
    });

    // 调用后端 API 标记所有为已读
    try {
      await followsApi.markAllViewed();
      // 重新获取最新状态（虽然本地已经乐观更新了）
      queryClient.invalidateQueries({ queryKey: ['follows'] });
    } catch (error) {
      console.error('Failed to mark notifications as viewed:', error);
    }
  };

  if (!open) {
    return null;
  }

  const handleGoToFollows = () => {
    navigate('/me?tab=follows');
    onClose();
  };

  return (
    <div className="od-floating-glass fixed inset-x-3 top-20 z-50 mx-auto flex max-h-[70vh] w-auto max-w-md flex-col items-stretch rounded-xl border border-[var(--od-border-strong)] shadow-2xl shadow-black/50 animate-in fade-in slide-in-from-top-2 sm:absolute sm:inset-x-auto sm:right-0 sm:top-full sm:mt-3 sm:max-h-[600px] sm:w-[360px]">
      <div className="flex items-start justify-between border-b border-[var(--od-border-strong)] px-4 py-3">
        <div>
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-[var(--od-accent)]" />
            <h2 className="text-sm font-semibold text-[var(--od-text-primary)]">通知中心</h2>
          </div>
          <p className="mt-1 text-xs text-[var(--od-text-secondary)]">
            包含关注帖子更新与索引页/系统更新公告。
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-7 w-7 items-center justify-center rounded-full text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
          aria-label="关闭通知中心"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex items-center justify-between px-4 py-2 text-xs text-[var(--od-text-secondary)]">
              <span>当前共有 {effectiveUnreadCount} 个关注更新</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleClearAllNotifications}
            className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
            title="清除所有通知"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={handleGoToFollows}
            className="text-[var(--od-accent)] hover:underline"
          >
            前往「我的关注」
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3 pt-1">
        {(isLoading || isStaticLoading) && (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, idx) => (
              <div
                key={idx}
                className="h-16 animate-pulse rounded-lg bg-[color-mix(in_oklab,var(--od-bg-secondary)_80%,transparent)]"
              />
            ))}
          </div>
        )}

        {(isError || isStaticError) && !(isLoading || isStaticLoading) && (
          <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-xs text-[var(--od-text-secondary)]">
            <AlertCircle className="h-5 w-5 text-[var(--od-error)]" />
            <p>加载通知失败，请稍后重试。</p>
          </div>
        )}

        {!isLoading && !isStaticLoading && !isError && !isStaticError && !hasAnyNotification && (
          <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-xs text-[var(--od-text-secondary)]">
            <Bell className="h-6 w-6 text-[var(--od-border-strong)]" />
            <p>当前没有新的通知。</p>
            <p>可以在「我的关注」中管理帖子更新。</p>
          </div>
        )}

        {!isLoading && !isStaticLoading && !isError && !isStaticError && hasAnyNotification && (
          <div className="space-y-2">
            {allNotifications.map((item) => (
              <div
                key={item.id}
                onClick={() => handleNotificationClick(item)}
                className="group cursor-pointer rounded-lg border border-[var(--od-border)] bg-[var(--od-card)] p-3 text-xs transition-colors hover:border-[var(--od-accent)] hover:bg-[color-mix(in_oklab,var(--od-bg-secondary)_85%,transparent)]"
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <p className="line-clamp-1 font-semibold text-[var(--od-text-primary)]">{item.title}</p>
                  <div className="flex items-center gap-1">
                    {item.kind === 'release_update' && (
                      <span className="rounded bg-[var(--od-bg-tertiary)] px-1.5 py-0.5 text-[10px] text-[var(--od-text-tertiary)]">
                        {item.source === 'system' ? '系统更新' : '索引页更新'}
                      </span>
                    )}
                    {item.created_at && (
                      <span className="whitespace-nowrap text-[10px] text-[var(--od-text-tertiary)]">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    )}
                    {item.kind !== 'follow_update' && (
                      <button
                        type="button"
                        onClick={(e) => handleDismissStatic(item.id, e)}
                        className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
                        aria-label="关闭该通知"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </div>
                {item.kind === 'follow_update' && item.thread && (
                  <div className="mb-2 flex items-start gap-2">
                    <div className="h-10 w-10 flex-shrink-0 overflow-hidden rounded-md bg-[var(--od-bg-tertiary)]">
                      {item.thread.thumbnail_urls && item.thread.thumbnail_urls.length > 0 ? (
                        <img
                          src={item.thread.thumbnail_urls[0]}
                          alt={item.title}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-[var(--od-text-tertiary)]">
                          <Bell className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-[11px] text-[var(--od-text-tertiary)]">
                        {item.thread.author?.display_name ??
                          item.thread.author?.global_name ??
                          item.thread.author?.name ??
                          '未知作者'}
                      </p>
                      <p className="line-clamp-2 text-[11px] text-[var(--od-text-secondary)]">
                        {item.message}
                      </p>
                    </div>
                  </div>
                )}
                {item.kind !== 'follow_update' && (
                  <p className="line-clamp-2 text-[var(--od-text-secondary)]">{item.message}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
