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
import { useFontSizeSetting, useCardSizeSetting } from '@/shared/hooks/useSettings';
import { fontSizeMap, cardSizeMap } from '@/shared/lib/settings';


interface ThreadCardProps {
  thread: Thread;
  onTagClick?: (tag: string) => void;
  searchQuery?: string;
  onAuthorClick?: (author: { id: string; name: string }) => void;
  onPreview?: (thread: Thread) => void;
}

function ThreadCardImpl({ thread, onTagClick, searchQuery, onAuthorClick, onPreview }: ThreadCardProps) {
  const navigate = useNavigate();
  const fontSize = useFontSizeSetting();
  const fontSizes = fontSizeMap[fontSize];
  const cardSize = useCardSizeSetting();
  const cardSizes = cardSizeMap[cardSize];
  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';
  const authorId = thread.author?.id || '';
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
      className={`group relative flex w-full cursor-pointer flex-col overflow-hidden rounded-[1.4rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-shell)]/30 backdrop-blur-[4px] shadow-[var(--od-shadow-soft)] transition-all duration-300 hover:-translate-y-1 hover:border-[color-mix(in_srgb,var(--od-accent)_28%,var(--od-border))] hover:bg-[var(--od-surface-shell)]/50 ${cardSizes.imageHeight}`}
      onClick={() => onPreview?.(thread)}
    >
      {/* Background Image Layer */}
      <div className="absolute inset-0 z-0">
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
          <div className="flex h-full w-full items-center justify-center bg-[color-mix(in_srgb,var(--od-surface-raised)_15%,transparent)]">
            <ImageIcon className="h-12 w-12 text-[var(--od-text-tertiary)]/20" />
          </div>
        )}
      </div>

      {/* Gradient Overlay - Theme aware fade to background color */}
      <div className="pointer-events-none absolute inset-0 z-10 bg-[linear-gradient(180deg,transparent_15%,color-mix(in_srgb,var(--od-bg)_35%,transparent)_45%,color-mix(in_srgb,var(--od-bg)_90%,transparent)_85%,var(--od-bg)_100%)]" />

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
      <div className={`absolute bottom-0 left-0 right-0 z-20 flex flex-col ${cardSizes.padding} text-[var(--od-text-primary)]`}>

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
                  className="od-card-tag border-[var(--od-border-strong)]/40 bg-[var(--od-surface-input)]/60 text-[var(--od-text-secondary)] hover:bg-[var(--od-surface-input)] text-[10px]"
                >
                  {tag}
              </button>
            ))}
            {/* Show +N for explicit tags */}
            {thread.tags.length > 3 && (
              <span className="od-card-tag border-[var(--od-border-strong)]/40 bg-[var(--od-surface-input)]/60 text-[var(--od-text-secondary)] text-[10px]">
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
                className="od-card-tag border-cyan-200/20 bg-cyan-500/20 text-white"
              >
                ~{tag}
              </span>
            ))}
          </div>
        )}

        {/* Title */}
        <h3
          ref={titleMeasureRef}
          className={`mb-2 font-extrabold leading-snug tracking-[-0.02em] ${cardSizes.titleLines} ${fontSizes.title} text-[var(--od-text-primary)]`}
        >
          <HighlightText text={clampedTitle} highlight={searchQuery} className="text-[var(--od-text-primary)]" />
        </h3>
        {hasExcerpt && (
          <p
            ref={excerptMeasureRef}
            className={`mb-3 ${cardSizes.contentLines} ${fontSizes.content} leading-snug text-[var(--od-text-secondary)]`}
          >
            {clampedExcerpt}
          </p>
        )}
        {/* Footer: Author + Time + Stats */}
        <div className={`border-t pt-3 ${fontSizes.meta} border-[var(--od-border-strong)]/30 text-[var(--od-text-secondary)]`}>
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2">
            <div className="flex min-w-0 items-center gap-2 overflow-hidden">
              <button
                type="button"
                onClick={handleAuthorClick}
                className="rounded-full"
              >
                <AuthorAvatar author={thread.author} className="h-6 w-6 md:h-7 md:w-7 ring-1 ring-[var(--od-border-strong)]/40" />
              </button>
              <button
                type="button"
                onClick={handleAuthorClick}
                className="max-w-[120px] truncate font-medium hover:text-[var(--od-text-primary)]"
              >
                {authorName}
              </button>
            </div>
            <div className="flex flex-col items-end gap-1.5 text-[10px] text-[var(--od-text-tertiary)]">
              <span className="text-[var(--od-border-strong)]/60">•</span>
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
