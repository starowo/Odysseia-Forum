import { MessageCircle, ThumbsUp, ExternalLink } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { LazyImage } from '@/components/common/LazyImage';
import { Tooltip } from '@/components/common/Tooltip';
import { HighlightText } from '@/components/common/HighlightText';
import type { Thread } from '@/types/thread.types';
import { useSettings } from '@/hooks/useSettings';
import { fontSizeMap, cardSizeMap } from '@/lib/settings';

interface ThreadCardProps {
  thread: Thread;
  onTagClick?: (tag: string) => void;
  searchQuery?: string;
  onAuthorClick?: (authorName: string) => void;
  onPreview?: (thread: Thread) => void;
}

export function ThreadCard({ thread, onTagClick, searchQuery, onAuthorClick, onPreview }: ThreadCardProps) {
  const { settings } = useSettings();
  const fontSizes = fontSizeMap[settings.fontSize];
  const cardSizes = cardSizeMap[settings.cardSize];

  const createdTime = formatDistanceToNow(new Date(thread.created_at), {
    addSuffix: true,
    locale: zhCN,
  });

  const articleBaseClasses =
    'group relative flex h-full flex-col overflow-hidden rounded-xl bg-[var(--od-card)] shadow-md transition-all duration-300 ease-out hover:-translate-y-1 hover:bg-[var(--od-card-hover)] hover:shadow-xl';

  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';

  // 构建Discord帖子链接
  // 如果guild_id不存在，使用环境变量中的GUILD_ID
  const guildId = thread.guild_id || import.meta.env.VITE_GUILD_ID || '@me';
  const discordUrl = `https://discord.com/channels/${guildId}/${thread.channel_id}/${thread.thread_id}`;

  const handleOpenThread = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Opening thread:', { 
      guild_id: thread.guild_id, 
      channel_id: thread.channel_id, 
      thread_id: thread.thread_id,
      url: discordUrl 
    });
    window.open(discordUrl, '_blank', 'noopener,noreferrer');
  };

  return (
    <article
      className={articleBaseClasses}
      onClick={() => onPreview?.(thread)}
    >
      {/* 大图片区域 - 列表态固定高度，预览浮层中再放大展示 */}
      <div
        className={`relative w-full overflow-hidden bg-[var(--od-bg-tertiary)] ${cardSizes.imageHeight}`}
      >
        {thread.thumbnail_url ? (
          <LazyImage
            src={thread.thumbnail_url}
            alt={thread.title}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          // 无图片时显示纯色背景
          <div className="h-full w-full bg-gradient-to-br from-[#18191c] to-[#1e1f22]" />
        )}

        {/* 有更新徽章：绿色毛玻璃效果 */}
        {thread.has_update && (
          <div className="absolute right-2 top-2 flex items-center gap-1 rounded-full bg-[#23a55a]/90 px-2 py-0.5 text-xs font-semibold text-white shadow-sm backdrop-blur-sm">
            <span className="inline-block h-2 w-2 rounded-full bg-white" />
            <span>有更新</span>
          </div>
        )}

        {/* 标签悬浮在图片上（左下角） */}
        {thread.tags && thread.tags.length > 0 && (
          <div className="absolute bottom-2 left-2 flex flex-wrap gap-1.5">
            {thread.tags.slice(0, 3).map((tag) => (
              <button
                key={tag}
                onClick={(e) => {
                  e.stopPropagation();
                  onTagClick?.(tag);
                }}
                className="rounded-md bg-black/80 px-2.5 py-1 text-xs font-medium text-white backdrop-blur-sm transition-all duration-200 hover:scale-105 hover:bg-black"
              >
                {tag}
              </button>
            ))}
            {thread.tags.length > 3 && (
              <span className="rounded-md bg-black/80 px-2.5 py-1 text-xs text-white backdrop-blur-sm">
                +{thread.tags.length - 3}
              </span>
            )}
          </div>
        )}
      </div>

      {/* 内容区域（图片下方） */}
      <div className={`flex flex-1 flex-col ${cardSizes.padding}`}>
        {/* 标题 - 支持关键词高亮和字体大小设置 */}
        <h3
          className={`mb-2 flex items-center gap-1 font-bold leading-snug text-[var(--od-text-primary)] transition-colors duration-200 ${fontSizes.title} ${cardSizes.titleLines}`}
        >
          {thread.is_following && (
            <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[#f23f43]" />
          )}
          <HighlightText text={thread.title} highlight={searchQuery} />
        </h3>

        {/* 作者信息 */}
        <div className={`mb-2 flex items-center gap-2 text-[var(--od-text-tertiary)] ${fontSizes.meta}`}>
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

        {/* 内容摘要 - 列表态仅展示固定高度的预览，全文阅读通过上层预览浮层完成 */}
        {thread.first_message_excerpt ? (
          <div
            className={`mb-3 overflow-y-auto scrollbar-thin ${
              settings.cardSize === 'compact'
                ? 'h-12'
                : settings.cardSize === 'large'
                  ? 'h-24'
                  : 'h-20'
            }`}
          >
            <p
              className={`leading-relaxed text-[var(--od-text-secondary)] ${fontSizes.content} ${cardSizes.contentLines}`}
            >
              <HighlightText text={thread.first_message_excerpt} highlight={searchQuery} />
            </p>
          </div>
        ) : (
          <div
            className={`mb-3 ${
              settings.cardSize === 'compact'
                ? 'h-12'
                : settings.cardSize === 'large'
                  ? 'h-24'
                  : 'h-20'
            }`}
          />
        )}

        {/* 底部统计信息 - 固定在底部 */}
        <div className="mt-auto flex items-center justify-between border-t border-[var(--od-border)] pt-2 text-xs text-[var(--od-text-tertiary)]">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <MessageCircle className="h-3.5 w-3.5" />
              {thread.reply_count}
            </span>
            <span className="flex items-center gap-1">
              <ThumbsUp className="h-3.5 w-3.5" />
              {thread.reaction_count}
            </span>
          </div>
          {/* 跳转按钮 */}
          <Tooltip content="在Discord中打开" position="left">
            <button
              onClick={handleOpenThread}
              className="flex items-center gap-1.5 rounded-lg bg-[var(--od-accent)] px-2.5 py-1 text-xs font-medium text-white transition-all duration-200 hover:scale-105 hover:bg-[var(--od-accent-hover)]"
              aria-label="在Discord中打开"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>打开</span>
            </button>
          </Tooltip>
        </div>
      </div>
    </article>
  );
}
