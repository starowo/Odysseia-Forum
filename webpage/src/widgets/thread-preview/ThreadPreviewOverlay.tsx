import { X, MessageCircle, ThumbsUp, Calendar, Hash, User, Eye, Clock3 } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { MarkdownText } from '@/shared/ui/MarkdownText';
import { ImageCarousel } from '@/entities/thread/ImageCarousel';
import { AuthorAvatar } from '@/entities/user/AuthorAvatar';
import { ThreadActions } from '@/features/threads/components/ThreadActions';
import { ThreadStatusBadges } from '@/entities/thread/ThreadStatusBadges';
import type { Thread } from '@/entities/thread/types';
import { useFontSizeSetting } from '@/shared/hooks/useSettings';
import { fontSizeMap } from '@/shared/lib/settings';
import { useLockBodyScroll } from '@/shared/hooks/useLockBodyScroll';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { addToken } from '@/shared/lib/searchTokenizer';

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
  const navigate = useNavigate();
  const location = useLocation();
  const { params, setParams } = useSearchURLParams();
  const fontSize = useFontSizeSetting();
  const fontSizes = fontSizeMap[fontSize];
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
  const lastActiveTime = thread.last_active_at
    ? formatDistanceToNow(new Date(thread.last_active_at), {
        addSuffix: true,
        locale: zhCN,
      })
    : null;
  const virtualOnlyTags = (thread.virtual_tags || []).filter((tag) => !thread.tags.includes(tag));

  const searchableAuthorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name;
  const authorName = searchableAuthorName || '未知用户';

  const applySearchToken = useCallback(
    (type: 'tag' | 'author', value: string) => {
      const nextQuery = addToken(params.query || '', type, value, 'include');

      if (location.pathname !== '/search') {
        navigate(nextQuery ? `/search?q=${encodeURIComponent(nextQuery)}` : '/search');
      } else {
        setParams({ query: nextQuery });
      }

      handleClose();
    },
    [location.pathname, navigate, params.query, setParams],
  );

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-300 ${isVisible ? 'bg-black/60 backdrop-blur-sm' : 'bg-black/0 backdrop-blur-none pointer-events-none'
        }`}
      onClick={handleClose}
    >
      <div
        className={`od-floating-panel-solid flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-[1.6rem] transition-all duration-300 ${isVisible ? 'translate-y-0 scale-100 opacity-100' : 'translate-y-4 scale-95 opacity-0'
          }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="border-b border-[var(--od-shell-line)] bg-[var(--od-surface-floating)] px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex flex-1 items-start gap-3">
              {thread.author?.id ? (
                <button
                  type="button"
                  onClick={() => {
                    handleClose();
                    navigate(`/u/${thread.author!.id}`);
                  }}
                  className="shrink-0"
                  title={`查看作者主页：${authorName}`}
                >
                  <AuthorAvatar author={thread.author} className="h-10 w-10 transition-opacity hover:opacity-80" />
                </button>
              ) : (
                <AuthorAvatar author={thread.author} className="h-10 w-10" />
              )}
              <div className="min-w-0">
                {thread.author?.id ? (
                  <button
                    type="button"
                    onClick={() => {
                      handleClose();
                      navigate(`/u/${thread.author!.id}`);
                    }}
                    className="truncate text-left font-bold text-[var(--od-text-primary)] hover:text-[var(--od-accent)] hover:underline"
                    title={`查看作者主页：${authorName}`}
                  >
                    {authorName}
                  </button>
                ) : (
                  <div className="truncate font-bold text-[var(--od-text-primary)]">{authorName}</div>
                )}
                <div className="mt-1">
                  <ThreadStatusBadges
                    isFollowing={thread.collected_flag}
                    hasUpdate={thread.has_update}
                    variant="detail"
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {!hideExternalButton && (
                <ThreadActions
                  threadId={thread.thread_id}
                  guildId={thread.guild_id}
                  size="sm"
                  alwaysVisible={true}
                  externalUrlOverride={externalUrlOverride}
                />
              )}
                <button
                  onClick={handleClose}
                  className="rounded-full p-2 text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-interactive-hover)] hover:text-[var(--od-text-primary)]"
                >
                  <X className="h-5 w-5" />
                </button>
            </div>
          </div>

          <div className="mt-3 grid gap-2 text-xs text-[var(--od-text-tertiary)]">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="inline-flex items-center gap-1" title={fullTime}>
                <Calendar className="h-3.5 w-3.5" />
                发布于 {createdTime}
              </span>
              {lastActiveTime && (
                <span className="inline-flex items-center gap-1">
                  <Clock3 className="h-3.5 w-3.5" />
                  活跃于 {lastActiveTime}
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="inline-flex items-center gap-1">
                <MessageCircle className="h-3.5 w-3.5" />
                {thread.reply_count}
              </span>
              <span className="inline-flex items-center gap-1">
                <ThumbsUp className="h-3.5 w-3.5" />
                {thread.reaction_count}
              </span>
              <span className="inline-flex items-center gap-1">
                <Eye className="h-3.5 w-3.5" />
                {thread.display_count}
              </span>
              <span className="inline-flex items-center gap-1">
                <User className="h-3.5 w-3.5" />
                ID: {thread.thread_id}
              </span>
            </div>
          </div>
        </div>

        {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto bg-[var(--od-surface-floating)] p-6 scrollbar-thin">
          {/* Title */}
          <h2 className={`mb-4 font-bold leading-tight text-[var(--od-text-primary)] ${fontSizes.title}`}>
            {thread.title}
          </h2>

          {/* Tags */}
          {thread.tags && thread.tags.length > 0 && (
            <div className="mb-6 flex flex-wrap gap-2">
              {thread.tags.map((tag) => (
                <button
                  type="button"
                  key={tag}
                  onClick={() => applySearchToken('tag', tag)}
                  className="od-pill-chip"
                  title={`添加标签筛选：${tag}`}
                >
                  <Hash className="h-3 w-3" />
                  {tag}
                </button>
              ))}
            </div>
          )}
          {virtualOnlyTags.length > 0 && (
            <div className="mb-6 flex flex-wrap gap-2">
              {virtualOnlyTags.map((tag) => (
                <button
                  type="button"
                  key={`vt-${tag}`}
                  onClick={() => applySearchToken('tag', tag)}
                  className="inline-flex items-center gap-1 rounded-full border border-[var(--od-accent)]/24 bg-[var(--od-accent)]/10 px-3 py-1 text-xs font-semibold text-[var(--od-accent)] transition-colors hover:bg-[var(--od-accent)]/18"
                  title={`添加标签筛选：${tag}`}
                >
                  <Hash className="h-3 w-3" />
                  {tag}
                </button>
              ))}
            </div>
          )}

          {/* Images */}
          {thread.thumbnail_urls && thread.thumbnail_urls.length > 0 && (
            <div className="mb-6 overflow-hidden rounded-[1.25rem] border border-[var(--od-shell-line)]">
              <ImageCarousel
                images={thread.thumbnail_urls}
                alt={thread.title}
                className="h-[300px] sm:h-[400px]"
              />
            </div>
          )}

          {/* Content Excerpt (Full) - Flat, no background */}
          {thread.first_message_excerpt && (
            <div className={`mb-6 ${fontSizes.content} text-[var(--od-text-secondary)]`}>
              <MarkdownText text={thread.first_message_excerpt} />
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
