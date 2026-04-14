import { MessageCircle, ThumbsUp, Eye, Clock3, Images } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { memo } from 'react';
import { useNavigate } from 'react-router-dom';

import { LazyImage } from '@/shared/ui/LazyImage';
import { HighlightText } from '@/shared/ui/HighlightText';
import { MarkdownText } from '@/shared/ui/MarkdownText';
import type { Thread } from '@/entities/thread/types';
import { useFontSizeSetting, useImageModeSetting } from '@/shared/hooks/useSettings';
import { fontSizeMap } from '@/shared/lib/settings';
import { ThreadActions } from '@/features/threads/components/ThreadActions';
import { AuthorAvatar } from '@/entities/user/AuthorAvatar';
import { ThreadStatusBadges } from '@/entities/thread/ThreadStatusBadges';
import { usePretextClampText } from '@/shared/hooks/usePretextClampText';

interface ThreadListItemProps {
  thread: Thread;
  onTagClick?: (tag: string) => void;
  searchQuery?: string;
  onAuthorClick?: (author: { id: string; name: string }) => void;
  onPreview?: (thread: Thread) => void;
}

function ThreadListItemImpl({ thread, onTagClick, searchQuery, onAuthorClick, onPreview }: ThreadListItemProps) {
  const navigate = useNavigate();
  const fontSize = useFontSizeSetting();
  const imageMode = useImageModeSetting();
  const fontSizes = fontSizeMap[fontSize];

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

  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';
  const authorId = thread.author?.id || '';
  const hasExcerpt = !!thread.first_message_excerpt && thread.first_message_excerpt.trim() !== '...';
  const thumbnails = imageMode === 'off' ? [] : (thread.thumbnail_urls || []).filter(Boolean).slice(0, 4);

  const { measureRef: titleMeasureRef, clampedText: clampedTitle } = usePretextClampText<HTMLHeadingElement>(
    thread.title,
    { maxLines: 2 },
  );

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
      className="group relative w-full cursor-pointer py-3 text-[var(--od-text-primary)] transition-colors duration-200"
      onClick={() => onPreview?.(thread)}
    >
      <div className="absolute inset-x-0 bottom-0 h-px bg-[linear-gradient(90deg,transparent,color-mix(in_srgb,var(--od-divider-strong)_60%,transparent),transparent)]" />

      <div className="flex flex-col gap-4 md:flex-row md:items-start md:gap-5">
        <div className="min-w-0 flex-1">
          <div className={`mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 ${fontSizes.meta} text-[var(--od-text-tertiary)]`}>
            <button type="button" onClick={handleAuthorClick} className="shrink-0 rounded-full">
              <AuthorAvatar author={thread.author} className="h-6 w-6 md:h-7 md:w-7" />
            </button>
            <button
              type="button"
              onClick={handleAuthorClick}
              className="max-w-[9rem] truncate font-medium text-[var(--od-text-secondary)] transition-colors hover:text-[var(--od-text-primary)]"
            >
              {authorName}
            </button>
            <span className="text-[var(--od-divider-strong)]/75">/</span>
            <span className="whitespace-nowrap">{createdTime}</span>
            {lastActiveTime && (
              <span className="inline-flex items-center gap-1 whitespace-nowrap">
                <Clock3 className="h-3 w-3" />
                活跃 {lastActiveTime}
              </span>
            )}
          </div>

          <div className="mb-3 flex items-start gap-2.5">
            <h3
              ref={titleMeasureRef}
              className={`min-w-0 flex-1 font-semibold leading-snug tracking-[-0.02em] text-[var(--od-text-primary)] transition-colors duration-200 group-hover:text-[var(--od-text-heading)] ${fontSizes.title}`}
            >
              <HighlightText text={clampedTitle} highlight={searchQuery} />
            </h3>
            <ThreadStatusBadges
              isFollowing={thread.collected_flag}
              hasUpdate={thread.has_update}
              variant="list"
              className="mt-0.5 shrink-0"
            />
          </div>

          {hasExcerpt && (
            <div
              className={`mb-3 od-md line-clamp-2 break-all leading-relaxed text-[var(--od-text-secondary)] md:max-w-[72ch] ${fontSizes.content}`}
            >
              <MarkdownText text={thread.first_message_excerpt!} />
            </div>
          )}

          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[var(--od-text-tertiary)] md:text-xs">
              {thread.tags?.slice(0, 4).map((tag) => (
                <button
                  key={tag}
                  onClick={(e) => {
                    e.stopPropagation();
                    onTagClick?.(tag);
                  }}
                  className="truncate transition-colors hover:text-[var(--od-text-primary)]"
                >
                  #{tag}
                </button>
              ))}
              {thread.tags && thread.tags.length > 4 && <span>+{thread.tags.length - 4}</span>}
              {virtualOnlyTags.slice(0, 2).map((tag) => (
                <span key={`vt-${tag}`} className="text-[var(--od-text-emphasis)]">
                  ~{tag}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-3 text-[11px] text-[var(--od-text-tertiary)] md:text-xs">
              <span className="inline-flex items-center gap-1 transition-colors group-hover:text-[var(--od-text-secondary)]">
                <MessageCircle className="h-3.5 w-3.5" />
                <span className="tabular-nums">{thread.reply_count}</span>
              </span>
              <span className="inline-flex items-center gap-1 transition-colors group-hover:text-[var(--od-text-secondary)]">
                <ThumbsUp className="h-3.5 w-3.5" />
                <span className="tabular-nums">{thread.reaction_count}</span>
              </span>
              <span className="inline-flex items-center gap-1 transition-colors group-hover:text-[var(--od-text-secondary)]">
                <Eye className="h-3.5 w-3.5" />
                <span className="tabular-nums">{thread.display_count}</span>
              </span>
            </div>

            <div className="ml-auto shrink-0 text-[var(--od-text-tertiary)] transition-colors group-hover:text-[var(--od-text-primary)]">
              <ThreadActions
                threadId={thread.thread_id}
                guildId={thread.guild_id}
                size="md"
                alwaysVisible
              />
            </div>
          </div>
        </div>

        {thumbnails.length > 0 && (
          <div className="shrink-0 md:w-[13.5rem] lg:w-[14.5rem]">
            <div className="grid h-[9.5rem] grid-cols-2 gap-1.5 md:h-[10.75rem]">
              {thumbnails.length === 1 && (
                <div className="relative col-span-2 overflow-hidden rounded-[1rem] bg-[var(--od-surface-shell)]">
                  <LazyImage
                    src={thumbnails[0]}
                    alt={`${thread.title} 缩略图 1`}
                    className="h-full w-full object-cover"
                    threadId={thread.thread_id}
                    channelId={thread.channel_id}
                  />
                </div>
              )}

              {thumbnails.length === 2 && (
                <>
                  {thumbnails.map((src, index) => (
                    <div
                      key={`${thread.thread_id}-${src}-${index}`}
                      className="relative overflow-hidden rounded-[1rem] bg-[var(--od-surface-shell)]"
                    >
                      <LazyImage
                        src={src}
                        alt={`${thread.title} 缩略图 ${index + 1}`}
                        className="h-full w-full object-cover"
                        threadId={thread.thread_id}
                        channelId={thread.channel_id}
                      />
                    </div>
                  ))}
                </>
              )}

              {thumbnails.length === 3 && (
                <>
                  <div className="relative row-span-2 overflow-hidden rounded-[1rem] bg-[var(--od-surface-shell)]">
                    <LazyImage
                      src={thumbnails[0]}
                      alt={`${thread.title} 缩略图 1`}
                      className="h-full w-full object-cover"
                      threadId={thread.thread_id}
                      channelId={thread.channel_id}
                    />
                  </div>
                  <div className="relative overflow-hidden rounded-[1rem] bg-[var(--od-surface-shell)]">
                    <LazyImage
                      src={thumbnails[1]}
                      alt={`${thread.title} 缩略图 2`}
                      className="h-full w-full object-cover"
                      threadId={thread.thread_id}
                      channelId={thread.channel_id}
                    />
                  </div>
                  <div className="relative overflow-hidden rounded-[1rem] bg-[var(--od-surface-shell)]">
                    <LazyImage
                      src={thumbnails[2]}
                      alt={`${thread.title} 缩略图 3`}
                      className="h-full w-full object-cover"
                      threadId={thread.thread_id}
                      channelId={thread.channel_id}
                    />
                  </div>
                </>
              )}

              {thumbnails.length === 4 && (
                <>
                  {thumbnails.map((src, index) => (
                    <div
                      key={`${thread.thread_id}-${src}-${index}`}
                      className="relative overflow-hidden rounded-[1rem] bg-[var(--od-surface-shell)]"
                    >
                      <LazyImage
                        src={src}
                        alt={`${thread.title} 缩略图 ${index + 1}`}
                        className="h-full w-full object-cover"
                        threadId={thread.thread_id}
                        channelId={thread.channel_id}
                      />
                      {index === 3 && (thread.thumbnail_urls?.length || 0) > thumbnails.length && (
                        <div className="absolute inset-0 flex items-end justify-end bg-[linear-gradient(180deg,transparent,rgba(0,0,0,0.42))] p-2 text-white">
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium tracking-[0.08em]">
                            <Images className="h-3 w-3" />
                            +{(thread.thumbnail_urls?.length || 0) - thumbnails.length}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </article>
  );
}

export const ThreadListItem = memo(ThreadListItemImpl);
