import { MessageCircle, ThumbsUp, Image as ImageIcon, Eye, Calendar, Clock3 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

import { HighlightText } from '@/shared/ui/HighlightText';
import type { Thread } from '@/entities/thread/types';
import { ThreadActions } from '@/features/threads/components/ThreadActions';
import { reportBrokenThreadThumbnail, subscribeThreadThumbnailRepair } from '@/features/threads/lib/thumbnailRepairQueue';
import { AuthorAvatar } from '@/entities/user/AuthorAvatar';
import { ThreadStatusBadges } from '@/entities/thread/ThreadStatusBadges';
import { usePretextClampText } from '@/shared/hooks/usePretextClampText';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { memo } from 'react';


interface ThreadCardProps {
  thread: Thread;
  onTagClick?: (tag: string) => void;
  searchQuery?: string;
  onAuthorClick?: (author: { id: string; name: string }) => void;
  onPreview?: (thread: Thread) => void;
}

function ThreadCardImpl({ thread, onTagClick, searchQuery, onAuthorClick, onPreview }: ThreadCardProps) {
  const navigate = useNavigate();
  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';
  const authorId = thread.author?.id || '';
  const hasThumbnail = thread.thumbnail_urls && thread.thumbnail_urls.length > 0;
  const initialThumbnail = useMemo(() => thread.thumbnail_urls?.[0] || '', [thread.thumbnail_urls]);
  const [thumbnailSrc, setThumbnailSrc] = useState(initialThumbnail);

  useEffect(() => {
    setThumbnailSrc(initialThumbnail);
  }, [initialThumbnail, thread.thread_id]);

  useEffect(() => {
    return subscribeThreadThumbnailRepair(thread.thread_id, (urls) => {
      if (urls.length > 0) setThumbnailSrc(urls[0]);
    });
  }, [thread.thread_id]);
  const createdTime = formatDistanceToNow(new Date(thread.created_at), {
    addSuffix: true,
    locale: zhCN,
  });
  const lastActiveTime = thread.last_active_at
    ? formatDistanceToNow(new Date(thread.last_active_at), {
        addSuffix: true,
        locale: zhCN,
      })
    : null;
  const virtualOnlyTags = (thread.virtual_tags || []).filter((tag) => !thread.tags.includes(tag));
  const hasExcerpt =
    !!thread.first_message_excerpt &&
    thread.first_message_excerpt.trim() !== '...';
  const compactAuthorTextClass =
    authorName.length > 14
      ? 'text-[11px] md:text-xs'
      : authorName.length > 9
        ? 'text-xs md:text-sm'
        : 'text-sm';
  const { measureRef: titleMeasureRef, clampedText: clampedTitle } =
    usePretextClampText<HTMLHeadingElement>(thread.title, { maxLines: 2 });
  const { measureRef: excerptMeasureRef, clampedText: clampedExcerpt } =
    usePretextClampText<HTMLParagraphElement>(thread.first_message_excerpt || '', {
      maxLines: 2,
      enabled: hasExcerpt,
    });

  const handleAuthorClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!authorId) return;
    if (onAuthorClick) {
      onAuthorClick({ id: authorId, name: authorName });
      return;
    }
    navigate(`/u/${authorId}`);
  };

  return (
    <article
      className="group relative flex aspect-[3/5] w-full cursor-pointer flex-col overflow-hidden rounded-[1.4rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-raised)] shadow-[var(--od-shadow-soft)] transition-all duration-300 hover:-translate-y-1 hover:border-[color-mix(in_srgb,var(--od-accent)_28%,var(--od-border))] md:aspect-[3/4]"
      onClick={() => onPreview?.(thread)}
    >
      {/* Background Image Layer */}
      <div className="absolute inset-0 z-0 bg-[var(--od-surface-shell)]">
        {thumbnailSrc ? (
          <img
            src={thumbnailSrc}
            alt={thread.title}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
            onError={() => {
              reportBrokenThreadThumbnail({
                threadId: thread.thread_id,
                channelId: thread.channel_id,
              });
            }}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-[linear-gradient(160deg,var(--od-surface-shell),var(--od-surface-raised))]">
            <ImageIcon className="h-12 w-12 text-[var(--od-text-tertiary)] opacity-40" />
          </div>
        )}
      </div>

      {/* Gradient Overlay - Only show for threads with images to ensure text readability */}
      {hasThumbnail && (
        <div className="pointer-events-none absolute inset-0 z-10 bg-[linear-gradient(180deg,rgba(7,10,18,0.06),rgba(7,10,18,0.4)_48%,rgba(7,10,18,0.88))]" />
      )}

      {!hasThumbnail && <div className="absolute inset-0 z-10 bg-[linear-gradient(180deg,transparent,rgba(7,10,18,0.16)_56%,rgba(7,10,18,0.26))]" />}

      {/* Top Right Actions */}
      <div className="absolute right-3 top-3 z-20 opacity-100 transition-opacity duration-200 md:opacity-0 md:group-hover:opacity-100">
        <ThreadActions
          threadId={thread.thread_id}
          guildId={thread.guild_id}
          variant="glass"
        />
      </div>

      {/* Status Badges */}
      <ThreadStatusBadges
        isFollowing={thread.collected_flag}
        hasUpdate={thread.has_update}
        variant="card"
      />

      {/* Bottom Content Area */}
      <div className={`absolute bottom-0 left-0 right-0 z-20 flex flex-col p-4 ${hasThumbnail ? 'text-white' : 'text-[var(--od-text-primary)]'}`}>

        {/* Tags */}
        {thread.tags && thread.tags.length > 0 && (
            <div className="mb-2.5 flex flex-wrap gap-1.5">
              {thread.tags.slice(0, 3).map((tag) => (
                <button
                key={tag}
                onClick={(e) => {
                  e.stopPropagation();
                  onTagClick?.(tag);
                }}
                  className={`rounded-full px-2.5 py-1 text-[10px] font-semibold transition-colors border ${hasThumbnail
                  ? 'border-white/10 bg-white/12 text-white/88 hover:bg-white/18'
                  : 'border-[var(--od-border)] bg-[var(--od-surface-input)] text-[var(--od-text-secondary)] hover:bg-[var(--od-interactive-hover)] hover:text-[var(--od-text-primary)]'
                   }`}
                >
                  {tag}
              </button>
            ))}
            {/* Show +N for explicit tags */}
            {thread.tags.length > 3 && (
              <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold border ${hasThumbnail
                ? 'border-white/10 bg-white/12 text-white/82'
                : 'border-[var(--od-border)] bg-[var(--od-surface-input)] text-[var(--od-text-secondary)]'
                 }`}>
                +{thread.tags.length - 3}
              </span>
            )}
          </div>
        )}
        {virtualOnlyTags.length > 0 && (
          <div className="mb-2.5 flex flex-wrap gap-1.5">
            {virtualOnlyTags.slice(0, 2).map((tag) => (
              <span
                key={`vt-${tag}`}
                className={`rounded-full px-2.5 py-1 text-[10px] font-semibold border ${hasThumbnail
                  ? 'border-cyan-200/22 bg-cyan-300/16 text-white'
                  : 'border-[var(--od-accent)]/18 bg-[var(--od-accent)]/10 text-[var(--od-accent)]'
                  }`}
              >
                ~{tag}
              </span>
            ))}
          </div>
        )}

        {/* Title */}
        <h3
          ref={titleMeasureRef}
          className={`mb-2 line-clamp-2 text-base font-extrabold leading-snug tracking-[-0.02em] md:text-[1.05rem] ${hasThumbnail ? 'text-white drop-shadow-[0_2px_12px_rgba(0,0,0,0.38)]' : 'text-[var(--od-text-primary)]'}`}
        >
          <HighlightText text={clampedTitle} highlight={searchQuery} className={hasThumbnail ? 'text-white' : 'text-[var(--od-text-primary)]'} />
        </h3>
        {hasExcerpt && (
          <p
            ref={excerptMeasureRef}
            className={`mb-3 line-clamp-2 text-xs leading-5 ${hasThumbnail ? 'text-white/76' : 'text-[var(--od-text-secondary)]'}`}
          >
            {clampedExcerpt}
          </p>
        )}
        {/* Footer: Author + Time + Stats */}
        <div className={`border-t pt-3 text-xs ${hasThumbnail ? 'border-white/10 text-white/80' : 'border-[var(--od-shell-line)] text-[var(--od-text-secondary)]'}`}>
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2">
            <div className="flex min-w-0 items-center gap-2 overflow-hidden">
              <button
                type="button"
                onClick={handleAuthorClick}
                className="rounded-full"
              >
                <AuthorAvatar author={thread.author} className={`h-6 w-6 md:h-7 md:w-7 ${hasThumbnail ? 'ring-1 ring-white/20' : 'ring-1 ring-[var(--od-border)]'}`} />
              </button>
              <button
                type="button"
                onClick={handleAuthorClick}
                className={`truncate font-semibold hover:underline ${compactAuthorTextClass} ${hasThumbnail ? 'hover:text-white' : 'hover:text-[var(--od-text-primary)]'}`}
              >
                {authorName}
              </button>
            </div>
            <div className={`flex flex-col items-end gap-1.5 text-[10px] ${hasThumbnail ? 'text-white/88' : 'text-[var(--od-text-tertiary)]'}`}>
              <div className="flex items-center gap-2 whitespace-nowrap">
                <span className="inline-flex items-center gap-1 shrink-0">
                  <Calendar className="h-3 w-3 shrink-0" />
                  <span>{createdTime}</span>
                </span>
                {lastActiveTime && (
                  <span className="inline-flex items-center gap-1 min-w-0">
                    <Clock3 className="h-3 w-3 shrink-0" />
                    <span className="truncate max-w-[88px] md:max-w-[120px]">活跃 {lastActiveTime}</span>
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 whitespace-nowrap">
                <span className="inline-flex items-center gap-1">
                  <MessageCircle className="h-3.5 w-3.5 opacity-80" />
                  {thread.reply_count}
                </span>
                <span className="inline-flex items-center gap-1">
                  <ThumbsUp className="h-3.5 w-3.5 opacity-80" />
                  {thread.reaction_count}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Eye className="h-3.5 w-3.5 opacity-80" />
                  {thread.display_count}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

export const ThreadCard = memo(ThreadCardImpl);
