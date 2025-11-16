import { Bell, X, AlertCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { followsApi } from '@/features/follows/api/followsApi';
import type { Thread } from '@/types/thread.types';
import { resolveStaticNotifications } from '@/features/notifications/notificationsConfig';

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
}

export function NotificationCenter({ open, onClose }: NotificationCenterProps) {
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['follows'],
    queryFn: followsApi.getFollows,
    staleTime: 60 * 1000,
  });

  const follows = data?.results ?? [];
  const unreadCount = data?.unread_count ?? 0;

  // 静态站点公告与问候语
  const staticDefs = resolveStaticNotifications();
  const staticNotifications: NotificationItem[] = staticDefs.map((def) => ({
    id: def.id,
    kind: def.kind,
    title: def.title,
    message: def.message,
    created_at: def.created_at,
  }));

  // 关注更新类通知
  const followNotifications: NotificationItem[] = follows
    .filter((thread) => thread.has_update)
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

  if (!open) {
    return null;
  }

  const handleGoToFollows = () => {
    navigate('/follows');
    onClose();
  };

  return (
    <div className="absolute left-full top-0 z-40 ml-3 flex h-full max-h-[600px] w-[360px] flex-col rounded-xl border border-[var(--od-border-strong)] bg-[var(--od-bg)] shadow-xl shadow-black/40 animate-in fade-in slide-in-from-left-2">
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
        <span>当前共有 {unreadCount} 个关注更新</span>
        <button
          type="button"
          onClick={handleGoToFollows}
          className="text-[var(--od-accent)] hover:underline"
        >
          前往「我的关注」
        </button>
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
                className="group rounded-lg border border-[var(--od-border)] bg-[var(--od-card)] p-3 text-xs transition-colors hover:border-[var(--od-accent)] hover:bg-[color-mix(in_oklab,var(--od-bg-secondary)_85%,transparent)]"
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <p className="line-clamp-1 font-semibold text-[var(--od-text-primary)]">{item.title}</p>
                  {item.created_at && (
                    <span className="whitespace-nowrap text-[10px] text-[var(--od-text-tertiary)]">
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  )}
                </div>
                <p className="line-clamp-2 text-[var(--od-text-secondary)]">{item.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}