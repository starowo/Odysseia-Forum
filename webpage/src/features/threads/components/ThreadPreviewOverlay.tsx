import { X, MessageCircle, ThumbsUp, Calendar, Hash, User } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { useEffect, useState } from 'react';

import { MarkdownText } from '@/components/common/MarkdownText';
import { MultiImageGrid } from './MultiImageGrid';
import { AuthorAvatar } from './AuthorAvatar';
import { ThreadActions } from './ThreadActions';
import { ThreadStatusBadges } from './ThreadStatusBadges';
import type { Thread } from '@/types/thread.types';
import { useSettings } from '@/hooks/useSettings';
import { fontSizeMap } from '@/lib/settings';
import { useLockBodyScroll } from '@/hooks/useLockBodyScroll';

interface ThreadPreviewOverlayProps {
  thread: Thread;
  onClose: () => void;
  externalUrlOverride?: string | null;
  hideExternalButton?: boolean;
}

export function ThreadPreviewOverlay({
  thread,
  onClose,
  externalUrlOverride,
  hideExternalButton,
}: ThreadPreviewOverlayProps) {
  const { settings } = useSettings();
  const fontSizes = fontSizeMap[settings.fontSize];
  const [isVisible, setIsVisible] = useState(false);

  useLockBodyScroll(true);

  useEffect(() => {
    setIsVisible(true);

    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    window.addEventListener('keydown', handleEsc);

    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, []);

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(onClose, 300);
  };

  const createdTime = formatDistanceToNow(new Date(thread.created_at), {
    addSuffix: true,
    locale: zhCN,
  });

  const fullTime = format(new Date(thread.created_at), 'yyyy年MM月dd日 HH:mm', {
    locale: zhCN,
  });

  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-300 ${isVisible ? 'bg-black/60 backdrop-blur-sm' : 'bg-black/0 backdrop-blur-none pointer-events-none'
        }`}
      onClick={handleClose}
    >
      <div
        className={`flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-[var(--od-card)] shadow-2xl transition-all duration-300 ${isVisible ? 'scale-100 opacity-100 translate-y-0' : 'scale-95 opacity-0 translate-y-4'
          }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--od-border)] bg-[var(--od-card)] px-6 py-4">
          <div className="flex items-center gap-3">
            <AuthorAvatar author={thread.author} className="h-10 w-10" />
            <div>
              <div className="font-bold text-[var(--od-text-primary)]">{authorName}</div>
              <div className="text-xs text-[var(--od-text-tertiary)]">
                发布于 {createdTime}
              </div>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="rounded-full p-2 text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          {/* Title */}
          <h2 className={`mb-4 font-bold leading-tight text-[var(--od-text-primary)] ${fontSizes.title}`}>
            {thread.title}
            <ThreadStatusBadges
              isFollowing={thread.is_following}
              hasUpdate={thread.has_update}
              variant="detail"
              className="ml-3 align-middle"
            />
          </h2>

          {/* Tags */}
          {thread.tags && thread.tags.length > 0 && (
            <div className="mb-6 flex flex-wrap gap-2">
              {thread.tags.map((tag) => (
                <span
                  key={tag}
                  className="flex items-center gap-1 rounded-md bg-[var(--od-bg-secondary)] px-2.5 py-1 text-xs font-medium text-[var(--od-text-secondary)]"
                >
                  <Hash className="h-3 w-3" />
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Images */}
          {((thread.thumbnail_urls && thread.thumbnail_urls.length > 0) || thread.thumbnail_url) && (
            <div className="mb-6 overflow-hidden rounded-xl border border-[var(--od-border)]">
              <MultiImageGrid
                images={thread.thumbnail_urls || [thread.thumbnail_url!]}
                alt={thread.title}
                className="w-full"
              />
            </div>
          )}

          {/* Content Excerpt (Full) - Flat, no background */}
          {thread.first_message_excerpt && (
            <div className={`mb-6 ${fontSizes.content} text-[var(--od-text-secondary)]`}>
              <MarkdownText text={thread.first_message_excerpt} />
            </div>
          )}

          {/* Meta Info - Flat Row */}
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-[var(--od-text-tertiary)] border-t border-[var(--od-border)] pt-6">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-4 w-4" />
              <span className="font-bold text-[var(--od-text-primary)]">{thread.reply_count}</span>
              <span>回复</span>
            </div>
            <div className="flex items-center gap-2">
              <ThumbsUp className="h-4 w-4" />
              <span className="font-bold text-[var(--od-text-primary)]">{thread.reaction_count}</span>
              <span>反应</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              <span>{fullTime}</span>
            </div>
            <div className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <span>ID: {thread.thread_id}</span>
            </div>
          </div>

          {/* Actions */}
          {!hideExternalButton && (
            <div className="mt-6 flex justify-end">
              <ThreadActions
                threadId={thread.thread_id}
                guildId={thread.guild_id}
                size="md"
                alwaysVisible={true}
                externalUrlOverride={externalUrlOverride}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}