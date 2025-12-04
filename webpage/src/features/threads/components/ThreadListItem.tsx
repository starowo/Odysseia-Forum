import { MessageCircle, ThumbsUp } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { LazyImage } from '@/components/common/LazyImage';

import { HighlightText } from '@/components/common/HighlightText';
import { MarkdownText } from '@/components/common/MarkdownText';
import type { Thread } from '@/types/thread.types';
import { useSettings } from '@/hooks/useSettings';
import { fontSizeMap } from '@/lib/settings';
import { ThreadActions } from './ThreadActions';
import { AuthorAvatar } from './AuthorAvatar';
import { ThreadStatusBadges } from './ThreadStatusBadges';

interface ThreadListItemProps {
  thread: Thread;
  onTagClick?: (tag: string) => void;
  searchQuery?: string;
  onAuthorClick?: (authorName: string) => void;
  onPreview?: (thread: Thread) => void;
}

export function ThreadListItem({ thread, onTagClick, searchQuery, onAuthorClick, onPreview }: ThreadListItemProps) {
  const { settings } = useSettings();
  const fontSizes = fontSizeMap[settings.fontSize];

  const createdTime = formatDistanceToNow(new Date(thread.created_at), {
    addSuffix: true,
    locale: zhCN,
  });

  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';

  const hasExcerpt =
    !!thread.first_message_excerpt &&
    thread.first_message_excerpt.trim() !== '...';

  return (
    <article
      className="group relative flex min-h-[8rem] w-full max-w-full gap-0 overflow-hidden rounded-xl bg-[var(--od-card)] shadow-md transition-all duration-300 hover:bg-[var(--od-card-hover)] hover:shadow-xl cursor-pointer md:h-48"
      onClick={() => onPreview?.(thread)}
    >
      {/* 左侧内容区 - 占据更多空间 */}
      <div className="flex flex-1 flex-col justify-between p-3 min-w-0 md:p-5">
        {/* 标题 */}
        <div>
          <h3
            className={`mb-1 font-bold leading-snug text-[var(--od-text-primary)] transition-colors duration-200 ${fontSizes.title} line-clamp-2 md:mb-2 break-all`}
          >
            <HighlightText text={thread.title} highlight={searchQuery} />
            <ThreadStatusBadges
              isFollowing={thread.is_following}
              hasUpdate={thread.has_update}
              variant="list"
              className="ml-2"
            />
          </h3>

          {/* 作者和时间 */}
          <div className={`mb-1 flex items-center gap-2 ${fontSizes.meta} text-[var(--od-text-tertiary)] md:mb-3`}>
            {/* 头像 */}
            <AuthorAvatar author={thread.author} className="h-6 w-6 md:h-8 md:w-8" />
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (authorName && onAuthorClick) {
                  onAuthorClick(authorName);
                }
              }}
              className="truncate font-medium text-[var(--od-accent)] hover:underline max-w-[80px] md:max-w-none"
            >
              {authorName}
            </button>
            <span>·</span>
            <span className="whitespace-nowrap">{createdTime}</span>
          </div>

          {/* 内容摘要 - 列表模式也使用 Markdown 渲染 */}
          {hasExcerpt && (
            <div
              className={`mb-1 od-md leading-relaxed text-[var(--od-text-secondary)] ${fontSizes.content} line-clamp-1 md:mb-3 md:line-clamp-2 break-all`}
            >
              <MarkdownText text={thread.first_message_excerpt!} />
            </div>
          )}
        </div>

        {/* 底部信息 */}
        <div className="flex items-center justify-between mt-2 md:mt-0">
          {/* 标签 */}
          <div className="flex flex-wrap gap-1.5 overflow-hidden h-6 md:h-auto">
            {thread.tags?.slice(0, 3).map((tag) => (
              <button
                key={tag}
                onClick={(e) => {
                  e.stopPropagation();
                  onTagClick?.(tag);
                }}
                className="rounded-md bg-[var(--od-bg-secondary)] px-2 py-0.5 text-[10px] font-medium text-[var(--od-text-secondary)] transition-colors duration-200 hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)] md:px-2.5 md:py-1 md:text-xs"
              >
                {tag}
              </button>
            ))}
            {thread.tags && thread.tags.length > 3 && (
              <span className="flex items-center text-[10px] text-[#949ba4] md:text-xs">+{thread.tags.length - 3}</span>
            )}
          </div>

          {/* 统计信息和跳转按钮 */}
          <div className="flex items-center gap-2 md:gap-4 shrink-0">
            <div className="flex items-center gap-2 md:gap-3">
              <div className="flex items-center gap-1 text-[var(--od-text-tertiary)]">
                <MessageCircle className="h-3 w-3 md:h-4 md:w-4" />
                <span className="text-xs md:text-sm">{thread.reply_count}</span>
              </div>
              <div className="flex items-center gap-1 text-[var(--od-text-tertiary)]">
                <ThumbsUp className="h-3 w-3 md:h-4 md:w-4" />
                <span className="text-xs md:text-sm">{thread.reaction_count}</span>
              </div>
            </div>

            {/* 跳转按钮 */}
            <div className="scale-90 md:scale-100">
              <ThreadActions
                threadId={thread.thread_id}
                guildId={thread.guild_id}
                size="md"
              />
            </div>
          </div>
        </div>
      </div>

      {/* 右侧图片区 - 带渐变遮罩，防止溢出 */}
      <div className="relative w-32 flex-shrink-0 overflow-hidden bg-[var(--od-bg-secondary)] md:w-80">
        {(thread.thumbnail_urls && thread.thumbnail_urls.length > 0) || thread.thumbnail_url ? (
          <>
            <LazyImage
              src={thread.thumbnail_urls?.[0] || thread.thumbnail_url!}
              alt={thread.title}
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
            {thread.thumbnail_urls && thread.thumbnail_urls.length > 1 && (
              <div className="absolute bottom-2 right-2 flex items-center gap-1 rounded-md bg-black/60 px-1.5 py-0.5 text-xs font-bold text-white backdrop-blur-sm">
                <span className="material-symbols-outlined text-[10px]">image</span>
                <span>{thread.thumbnail_urls.length}</span>
              </div>
            )}
            {/* 左侧渐变遮罩 - 柔和过渡 */}
            <div className="pointer-events-none absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[color-mix(in_oklab,var(--od-bg-tertiary)_60%,transparent)] to-transparent transition-colors duration-300 group-hover:from-[var(--od-card-hover)] group-hover:via-[color-mix(in_oklab,var(--od-card-hover)_60%,transparent)] md:w-24" />
            {/* 整体暗化遮罩 - 柔和 */}
            <div className="pointer-events-none absolute inset-0 bg-black/10 transition-opacity duration-300 group-hover:bg-black/5" />
          </>
        ) : (
          <div className="h-full w-full bg-[var(--od-bg-secondary)]" />
        )}
      </div>
    </article>
  );
}
