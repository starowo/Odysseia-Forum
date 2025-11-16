import { MessageCircle, ThumbsUp, ExternalLink } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { LazyImage } from '@/components/common/LazyImage';
import { Tooltip } from '@/components/common/Tooltip';
import { HighlightText } from '@/components/common/HighlightText';
import type { Thread } from '@/types/thread.types';
import { useSettings } from '@/hooks/useSettings';
import { fontSizeMap } from '@/lib/settings';

interface ThreadListItemProps {
  thread: Thread;
  onTagClick?: (tag: string) => void;
  searchQuery?: string;
  onAuthorClick?: (authorName: string) => void;
}

export function ThreadListItem({ thread, onTagClick, searchQuery, onAuthorClick }: ThreadListItemProps) {
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

  const guildId = thread.guild_id || import.meta.env.VITE_GUILD_ID || '@me';
  const discordUrl = `https://discord.com/channels/${guildId}/${thread.channel_id}/${thread.thread_id}`;

  const handleOpenThread = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    window.open(discordUrl, '_blank', 'noopener,noreferrer');
  };

  return (
    <article className="group relative flex gap-0 overflow-hidden rounded-xl bg-[var(--od-card)] shadow-md transition-all duration-300 hover:bg-[var(--od-card-hover)] hover:shadow-xl">
      {/* 左侧内容区 - 占据更多空间 */}
      <div className="flex flex-1 flex-col justify-between p-5">
        {/* 标题 */}
        <div>
          <h3
            className={`mb-2 flex items-center gap-1 font-bold leading-snug text-[var(--od-text-primary)] transition-colors duration-200 ${fontSizes.title} line-clamp-2`}
          >
            {thread.is_following && (
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[#f23f43]" />
            )}
            <HighlightText text={thread.title} highlight={searchQuery} />
          </h3>

          {/* 作者和时间 */}
          <div className={`mb-3 flex items-center gap-2 ${fontSizes.meta} text-[var(--od-text-tertiary)]`}>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (authorName && onAuthorClick) {
                  onAuthorClick(authorName);
                }
              }}
              className="font-medium text-[var(--od-link)] hover:underline"
            >
              {authorName}
            </button>
            <span>·</span>
            <span>{createdTime}</span>
          </div>

          {/* 内容摘要 */}
          {thread.first_message_excerpt && (
            <p className={`mb-3 leading-relaxed text-[var(--od-text-secondary)] ${fontSizes.content} line-clamp-3`}>
              <HighlightText text={thread.first_message_excerpt} highlight={searchQuery} />
            </p>
          )}
        </div>

        {/* 底部信息 */}
        <div className="flex items-center justify-between">
          {/* 标签 */}
          <div className="flex flex-wrap gap-1.5">
            {thread.tags?.slice(0, 3).map((tag) => (
              <button
                key={tag}
                onClick={(e) => {
                  e.stopPropagation();
                  onTagClick?.(tag);
                }}
                className="rounded-md bg-[var(--od-bg-secondary)] px-2.5 py-1 text-xs font-medium text-[var(--od-text-secondary)] transition-colors duration-200 hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]"
              >
                {tag}
              </button>
            ))}
            {thread.tags && thread.tags.length > 3 && (
              <span className="flex items-center text-xs text-[#949ba4]">+{thread.tags.length - 3}</span>
            )}
          </div>

          {/* 统计信息和跳转按钮 */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 text-[var(--od-text-tertiary)]">
                <MessageCircle className="h-4 w-4" />
                <span className="text-sm">{thread.reply_count}</span>
              </div>
              <div className="flex items-center gap-1 text-[var(--od-text-tertiary)]">
                <ThumbsUp className="h-4 w-4" />
                <span className="text-sm">{thread.reaction_count}</span>
              </div>
            </div>
            
            {/* 跳转按钮 */}
            <Tooltip content="在 Discord 中打开" position="left">
              <button
                onClick={handleOpenThread}
                className="flex items-center gap-1.5 rounded-lg bg-[var(--od-accent)] px-3 py-1.5 text-sm font-medium text-white transition-all duration-200 hover:bg-[var(--od-accent-hover)]"
              >
                <ExternalLink className="h-4 w-4" />
                <span>打开</span>
              </button>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* 右侧图片区 - 带渐变遮罩，防止溢出 */}
      <div className="relative w-80 flex-shrink-0 overflow-hidden bg-[var(--od-bg-secondary)]">
        {thread.thumbnail_url ? (
          <>
            <LazyImage
              src={thread.thumbnail_url}
              alt={thread.title}
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
            {/* 左侧渐变遮罩 - 柔和过渡 */}
            <div className="pointer-events-none absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[color-mix(in_oklab,var(--od-bg-tertiary)_60%,transparent)] to-transparent transition-colors duration-300 group-hover:from-[var(--od-card-hover)] group-hover:via-[color-mix(in_oklab,var(--od-card-hover)_60%,transparent)]" />
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
