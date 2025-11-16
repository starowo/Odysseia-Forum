import { Bell, X, AlertCircle, Trash2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { followsApi } from '@/features/follows/api/followsApi';
import type { Thread } from '@/types/thread.types';
import { resolveStaticNotifications } from '@/features/notifications/notificationsConfig';
import { ThreadPreviewOverlay } from '@/features/threads/components/ThreadPreviewOverlay';

type NotificationKind = 'follow_update' | 'site_announcement' | 'greeting';

interface NotificationItem {
  id: string;
  kind: NotificationKind;
  title: string;
  message: string;
  created_at?: string;
  thread?: Thread;
}

interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
  onUnreadChange?: (count: number) => void;
}

export function NotificationCenter({ open, onClose, onUnreadChange }: NotificationCenterProps) {
  const navigate = useNavigate();

  // 通知详情预览（使用 ThreadPreviewOverlay 复用上浮浮层）
  const [preview, setPreview] = useState<{
    thread: Thread;
    externalUrlOverride?: string | null;
    hideExternalButton?: boolean;
    notificationId?: string;
    isFollowUpdate?: boolean;
  } | null>(null);

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

  const [dismissedFollowIds, setDismissedFollowIds] = useState<string[]>([]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['follows'],
    queryFn: followsApi.getFollows,
    staleTime: 60 * 1000,
  });

  const follows = data?.results ?? [];
  const unreadCount = data?.unread_count ?? 0;

  // 静态站点公告与问候语（可永久关闭）
  const staticDefs = resolveStaticNotifications();
  const staticNotifications: NotificationItem[] = staticDefs
    .filter((def) => !dismissedStaticIds.includes(def.id))
    .map((def) => ({
      id: def.id,
      kind: def.kind,
      title: def.title,
      message: def.message,
      created_at: def.created_at,
    }));

  // 关注更新类通知
  const followNotifications: NotificationItem[] = follows
    .filter((thread) => thread.has_update)
    .filter((thread) => !dismissedFollowIds.includes(`follow-${thread.thread_id}`))
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
  const effectiveUnreadCount = Math.max(unreadCount - dismissedFollowIds.length, 0);
  const unreadTotal = allNotifications.length;

  // 将当前未读通知数量回传给父级（用于侧边栏铃铛动画和红点）
  useEffect(() => {
    onUnreadChange?.(unreadTotal);
  }, [unreadTotal, onUnreadChange]);

  const handleNotificationClick = (item: NotificationItem) => {
    // 关注帖子更新：点击即视为已读，从列表中移除，并打开详情预览
    if (item.kind === 'follow_update' && item.thread) {
      setDismissedFollowIds((prev) => (prev.includes(item.id) ? prev : [...prev, item.id]));

      setPreview({
        thread: item.thread,
        notificationId: item.id,
        isFollowUpdate: true,
      });
      return;
    }

    // 静态公告 / 问候：点击后也视为已读，从列表中移除，同时用预览浮层展示 Markdown 文本（不显示「在 Discord 中打开」按钮）
    setDismissedStaticIds((prev) => (prev.includes(item.id) ? prev : [...prev, item.id]));

    const pseudoThread: Thread = {
      thread_id: `notification-${item.id}`,
      channel_id: '',
      title: item.title,
      first_message_excerpt: item.message,
      created_at: new Date(item.created_at ?? Date.now()).toISOString(),
      reaction_count: 0,
      reply_count: 0,
      tags: [],
    };

    setPreview({
      thread: pseudoThread,
      hideExternalButton: true,
      externalUrlOverride: null,
      notificationId: item.id,
      isFollowUpdate: false,
    });
  };

  const handleDismissStatic = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDismissedStaticIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
  };

  const handleClearAllNotifications = () => {
    // 静态通知：全部标记为已关闭
    setDismissedStaticIds((prev) => {
      const allStaticIds = staticDefs.map((d) => d.id);
      const merged = Array.from(new Set([...prev, ...allStaticIds]));
      return merged;
    });

    // 关注更新通知：基于当前 has_update 的帖子全部标记为已读
    const allFollowIds = follows
      .filter((thread) => thread.has_update)
      .map((thread) => `follow-${thread.thread_id}`);

    setDismissedFollowIds((prev) => Array.from(new Set([...prev, ...allFollowIds])));
  };

  const handleClosePreview = () => {
    setPreview(null);
  };

  if (!open) {
    return null;
  }

  const handleGoToFollows = () => {
    navigate('/follows');
    onClose();
  };

  return (
    <div className="fixed inset-x-3 top-16 z-40 mx-auto flex max-h-[70vh] w-auto max-w-md flex-col rounded-xl border border-[var(--od-border-strong)] bg-[var(--od-bg)] shadow-xl shadow-black/40 animate-in fade-in slide-in-from-left-2 md:absolute md:inset-x-auto md:left-full md:top-0 md:ml-3 md:h-full md:max-h-[600px] md:w-[360px]">
      <div className="flex items-start justify-between border-b border-[var(--od-border-strong)] px-4 py-3">
        <div>
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-[var(--od-accent)]" />
            <h2 className="text-sm font-semibold text-[var(--od-text-primary)]">通知中心</h2>
          </div>
          <p className="mt-1 text-xs text-[var(--od-text-secondary)]">
            关注的帖子有更新时，会在这里显示摘要。
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
        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, idx) => (
              <div
                key={idx}
                className="h-16 animate-pulse rounded-lg bg-[color-mix(in_oklab,var(--od-bg-secondary)_80%,transparent)]"
              />
            ))}
          </div>
        )}

        {isError && !isLoading && (
          <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-xs text-[var(--od-text-secondary)]">
            <AlertCircle className="h-5 w-5 text-[var(--od-error)]" />
            <p>加载通知失败，请稍后重试。</p>
          </div>
        )}

        {!isLoading && !isError && !hasAnyNotification && (
          <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-xs text-[var(--od-text-secondary)]">
            <Bell className="h-6 w-6 text-[var(--od-border-strong)]" />
            <p>当前没有新的关注更新。</p>
            <p>可以在「我的关注」中管理你感兴趣的帖子。</p>
          </div>
        )}

        {!isLoading && !isError && hasAnyNotification && (
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
                <p className="line-clamp-2 text-[var(--od-text-secondary)]">{item.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {preview && (
        <ThreadPreviewOverlay
          thread={preview.thread}
          onClose={handleClosePreview}
          externalUrlOverride={preview.externalUrlOverride}
          hideExternalButton={preview.hideExternalButton}
        />
      )}
    </div>
  );
}