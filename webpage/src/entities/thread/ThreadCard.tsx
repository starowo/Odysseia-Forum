import { MessageCircle, ThumbsUp, Image as ImageIcon, Eye, Calendar, Clock3 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { useEffect, useMemo, useRef, useState, memo } from 'react';
import { useNavigate } from 'react-router-dom';

import { HighlightText } from '@/shared/ui/HighlightText';
import { DiscordMarkdownText } from '@/shared/ui/DiscordMarkdownText';
import type { Thread } from '@/entities/thread/types';
import { ThreadActions } from '@/features/threads/components/ThreadActions';
import { reportBrokenThreadThumbnail, subscribeThreadThumbnailRepair } from '@/features/threads/lib/thumbnailRepairQueue';
import { AuthorAvatar } from '@/entities/user/AuthorAvatar';
import { ThreadStatusBadges } from '@/entities/thread/ThreadStatusBadges';
import { useFontSizeSetting, useCardSizeSetting } from '@/shared/hooks/useSettings';
import { fontSizeMap } from '@/shared/lib/settings';

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

  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';
  const authorId = thread.author?.id || '';
  const initialThumbnail = useMemo(() => thread.thumbnail_urls?.[0] || '', [thread.thumbnail_urls]);
  const [thumbnailSrc, setThumbnailSrc] = useState(initialThumbnail);
  const titleViewportRef = useRef<HTMLSpanElement>(null);
  const titleTrackRef = useRef<HTMLSpanElement>(null);
  const [titleShift, setTitleShift] = useState(0);
  const [isTitleHovered, setIsTitleHovered] = useState(false);
  const shouldMarquee = isTitleHovered && titleShift > 0;

  useEffect(() => {
    setThumbnailSrc(initialThumbnail);
  }, [initialThumbnail, thread.thread_id]);

  useEffect(() => {
    return subscribeThreadThumbnailRepair(thread.thread_id, (urls) => {
      if (urls.length > 0) setThumbnailSrc(urls[0]);
    });
  }, [thread.thread_id]);

  useEffect(() => {
    const updateTitleShift = () => {
      const viewportWidth = titleViewportRef.current?.clientWidth || 0;
      const trackWidth = titleTrackRef.current?.scrollWidth || 0;
      setTitleShift(Math.max(trackWidth - viewportWidth + 12, 0));
    };

    updateTitleShift();
    window.addEventListener('resize', updateTitleShift);
    return () => window.removeEventListener('resize', updateTitleShift);
  }, [thread.title, fontSize, searchQuery]);

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
  const hasExcerpt = !!thread.first_message_excerpt && thread.first_message_excerpt.trim() !== '...';

  const handleAuthorClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!authorId) return;
    if (onAuthorClick) {
      onAuthorClick({ id: authorId, name: authorName });
      return;
    }
    navigate(`/u/${authorId}`);
  };

  const mediaAspectClass =
    cardSize === 'compact'
      ? 'aspect-[3/4]'
      : cardSize === 'large'
      ? 'aspect-[5/7]'
      : 'aspect-[3/4]';

  return (
    <article
      className="group flex h-full w-full cursor-pointer flex-col"
      onClick={() => onPreview?.(thread)}
    >
      <div className="flex flex-col gap-2 px-1 pb-3 pt-1 text-[var(--od-text-primary)]">
        <div className="flex min-w-0 items-center gap-2 overflow-hidden">
          <button type="button" onClick={handleAuthorClick} className="rounded-full shrink-0">
            <AuthorAvatar author={thread.author} className="h-6 w-6 md:h-7 md:w-7 ring-1 ring-[var(--od-border-strong)]/25" />
          </button>
          <div className="min-w-0 flex-1">
            <button
              type="button"
              onClick={handleAuthorClick}
              className="block max-w-[140px] truncate text-xs font-medium text-[var(--od-text-secondary)] transition-colors duration-200 group-hover:text-[var(--od-text-primary)] hover:text-[var(--od-text-primary)]"
            >
              {authorName}
            </button>
            <div className="mt-0.5 flex items-center gap-2 text-[10px] text-[var(--od-text-tertiary)]">
              <span className="inline-flex items-center gap-1 whitespace-nowrap">
                <Calendar className="h-3 w-3 shrink-0" />
                <span>{createdTime}</span>
              </span>
              {lastActiveTime && (
                <span className="inline-flex items-center gap-1 min-w-0 whitespace-nowrap">
                  <Clock3 className="h-3 w-3 shrink-0" />
                  <span className="truncate max-w-[88px]">活跃 {lastActiveTime}</span>
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="overflow-hidden">
          <h3
            className={`whitespace-nowrap ${fontSizes.title} text-[var(--od-text-primary)] transition-colors duration-200 group-hover:text-[color-mix(in_srgb,var(--od-text-primary)_82%,var(--od-accent))]`}
          >
            <span
              ref={titleViewportRef}
              className="inline-block max-w-full overflow-hidden align-top"
              onMouseEnter={() => setIsTitleHovered(true)}
              onMouseLeave={() => setIsTitleHovered(false)}
            >
              <span
                ref={titleTrackRef}
                style={{
                  ['--od-marquee-distance' as string]: `${titleShift}px`,
                  ['--od-marquee-gap' as string]: '1.75rem',
                  ['--od-marquee-duration' as string]: `${Math.max(5, titleShift / 22)}s`,
                }}
                className={`od-marquee-track inline-flex items-center font-extrabold leading-snug tracking-[-0.02em] ${
                  shouldMarquee ? 'od-marquee-active' : ''
                }`}
              >
                <span className="shrink-0">
                  <HighlightText text={thread.title} highlight={searchQuery} className="text-[var(--od-text-primary)]" />
                </span>
                {titleShift > 0 && (
                  <>
                    <span className="mx-7 shrink-0 text-[var(--od-text-tertiary)]/55">/</span>
                    <span className="shrink-0">
                      <HighlightText text={thread.title} highlight={searchQuery} className="text-[var(--od-text-primary)]" />
                    </span>
                  </>
                )}
              </span>
            </span>
          </h3>
        </div>
      </div>

      <div
        className={`relative w-full overflow-hidden rounded-[1.45rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-shell)] shadow-[var(--od-shadow-soft)] ${mediaAspectClass}`}
      >
        {thumbnailSrc ? (
          <img
            src={thumbnailSrc}
            alt={thread.title}
            className="h-full w-full object-cover"
            onError={() => {
              setThumbnailSrc('');
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

        <div className="absolute right-3 top-3 z-20 opacity-100 transition-opacity duration-200 md:opacity-0 md:group-hover:opacity-100">
          <ThreadActions threadId={thread.thread_id} guildId={thread.guild_id} variant="glass" />
        </div>

        <ThreadStatusBadges
          isFollowing={thread.collected_flag}
          hasUpdate={thread.has_update}
          variant="card"
        />
      </div>

      <div className="flex flex-1 flex-col gap-3 px-1 pt-3 text-[var(--od-text-primary)]">
        <div className="min-h-[2.75rem]">
          {hasExcerpt && (
            <p className={`${fontSizes.content} line-clamp-2 leading-relaxed text-[var(--od-text-secondary)] transition-colors duration-200 group-hover:text-[color-mix(in_srgb,var(--od-text-secondary)_72%,var(--od-text-primary))]`}>
              <DiscordMarkdownText text={thread.first_message_excerpt || ''} />
            </p>
          )}
        </div>

        <div className="min-h-[2.75rem] content-start">
          {(thread.tags.length > 0 || virtualOnlyTags.length > 0) && (
            <div className="flex flex-wrap gap-1.5">
              {thread.tags.slice(0, 3).map((tag) => (
                <button
                  key={tag}
                  onClick={(e) => {
                    e.stopPropagation();
                    onTagClick?.(tag);
                  }}
                  className="rounded-md border border-[var(--od-border)]/30 bg-[var(--od-surface-raised)]/60 px-2 py-0.5 text-[10px] text-[var(--od-text-secondary)] transition-colors hover:bg-[var(--od-surface-raised)] hover:text-[var(--od-text-primary)]"
                >
                  {tag}
                </button>
              ))}
              {thread.tags.length > 3 && (
                <span className="rounded-md border border-[var(--od-border)]/30 bg-[var(--od-surface-raised)]/60 px-2 py-0.5 text-[10px] text-[var(--od-text-secondary)]">
                  +{thread.tags.length - 3}
                </span>
              )}
              {virtualOnlyTags.slice(0, 2).map((tag) => (
                <span
                  key={`vt-${tag}`}
                  className="rounded-md border border-cyan-200/20 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-500"
                >
                  ~{tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="mt-auto grid grid-cols-3 gap-2 text-[var(--od-text-tertiary)]">
          <span className="inline-flex min-w-0 items-center gap-1 text-[11px]" title="浏览量">
            <Eye className="h-3.5 w-3.5 shrink-0" />
            <span className="min-w-0 truncate text-[clamp(9px,1.8vw,11px)] font-medium tabular-nums">
              {thread.display_count}
            </span>
          </span>
          <span className="inline-flex min-w-0 items-center gap-1 text-[11px]" title="回复数">
            <MessageCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="min-w-0 truncate text-[clamp(9px,1.8vw,11px)] font-medium tabular-nums">
              {thread.reply_count}
            </span>
          </span>
          <span className="inline-flex min-w-0 items-center gap-1 text-[11px]" title="点赞数">
            <ThumbsUp className="h-3.5 w-3.5 shrink-0" />
            <span className="min-w-0 truncate text-[clamp(9px,1.8vw,11px)] font-medium tabular-nums">
              {thread.reaction_count}
            </span>
          </span>
        </div>

        <div className="h-px w-full bg-[linear-gradient(90deg,transparent,color-mix(in_srgb,var(--od-border-strong)_36%,transparent),transparent)]" />
      </div>
    </article>
  );
}

export const ThreadCard = memo(ThreadCardImpl);
