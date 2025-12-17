import { useState, useRef, useEffect } from 'react';
import { MessageCircle, ThumbsUp, RefreshCw, Image as ImageIcon } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { toast } from 'sonner';

import { HighlightText } from '@/components/common/HighlightText';
import type { Thread } from '@/types/thread.types';
import { useSettings } from '@/hooks/useSettings';
import { fetchImagesApi } from '@/features/threads/api/fetchImagesApi';
import { MultiImageGrid } from './MultiImageGrid';
import { ThreadActions } from './ThreadActions';
import { AuthorAvatar } from './AuthorAvatar';
import { ThreadStatusBadges } from './ThreadStatusBadges';
import { MotionWrapper } from '@/components/ui/animation/MotionWrapper';

interface ThreadCardProps {
  thread: Thread;
  onTagClick?: (tag: string) => void;
  searchQuery?: string;
  onAuthorClick?: (authorName: string) => void;
  onPreview?: (thread: Thread) => void;
}

export function ThreadCard({ thread, onTagClick, searchQuery, onAuthorClick, onPreview }: ThreadCardProps) {
  const { settings } = useSettings();
  const imageLayerRef = useRef<HTMLDivElement>(null);

  const createdTime = formatDistanceToNow(new Date(thread.created_at), {
    addSuffix: true,
    locale: zhCN,
  });

  const authorName = thread.author?.name || 'Unknown User';
  const avatarUrl = thread.author?.avatar_url;
  const hasThumbnail = thread.thumbnail_urls && thread.thumbnail_urls.length > 0;

  // 使用搜索页面的 Store 获取高亮词
  const [isRefreshing, setIsRefreshing] = useState(false);

  // --- Parallax Effect ---
  useEffect(() => {
    const card = imageLayerRef.current?.parentElement;
    if (!card || !imageLayerRef.current) return;

    const MAX_MOVE = 15; // Max pixels to move

    const onCardMouseMove = (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const cardCenterX = rect.left + rect.width / 2;
      const cardCenterY = rect.top + rect.height / 2;

      // Calculate relative to card center
      const mouseX = (e.clientX - cardCenterX) / (rect.width / 2);
      const mouseY = (e.clientY - cardCenterY) / (rect.height / 2);

      const moveX = mouseX * -MAX_MOVE;
      const moveY = mouseY * -MAX_MOVE;

      if (imageLayerRef.current) {
        imageLayerRef.current.style.transform = `translate(${moveX}px, ${moveY}px) scale(1.1)`;
      }
    };

    const onCardMouseLeave = () => {
      if (imageLayerRef.current) {
        imageLayerRef.current.style.transform = `translate(0px, 0px) scale(1.0)`;
      }
    }

    const handleDeviceOrientation = (e: DeviceOrientationEvent) => {
      const tiltX = (e.gamma || 0) / 45; // Left/Right
      const tiltY = (e.beta || 0) / 45;  // Front/Back

      const clampedX = Math.max(-1, Math.min(1, tiltX));
      const clampedY = Math.max(-1, Math.min(1, tiltY));

      const moveX = clampedX * -MAX_MOVE;
      const moveY = clampedY * -MAX_MOVE;

      if (imageLayerRef.current) {
        imageLayerRef.current.style.transform = `translate(${moveX}px, ${moveY}px) scale(1.1)`;
      }
    };

    // Desktop
    card.addEventListener('mousemove', onCardMouseMove);
    card.addEventListener('mouseleave', onCardMouseLeave);

    // Mobile (Gyroscope)
    if (window.DeviceOrientationEvent && 'ontouchstart' in window) {
      window.addEventListener('deviceorientation', handleDeviceOrientation);
    }

    return () => {
      card.removeEventListener('mousemove', onCardMouseMove);
      card.removeEventListener('mouseleave', onCardMouseLeave);
      if (window.DeviceOrientationEvent) {
        window.removeEventListener('deviceorientation', handleDeviceOrientation);
      }
    };
  }, []);

  const handleRefreshImage = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isRefreshing) return;

    setIsRefreshing(true);
    try {
      const result = await fetchImagesApi.refresh([{
        thread_id: Number(thread.thread_id),
        channel_id: Number(thread.channel_id)
      }]);

      const item = result.results[0];
      if (item && item.updated) {
        toast.success('封面图已刷新');
      } else if (item?.error) {
        toast.error(`刷新失败: ${item.error} `);
      } else {
        toast.info('未发现新图片');
      }
    } catch (error) {
      toast.error('刷新请求失败');
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <MotionWrapper
      as="article"
      className="group relative flex aspect-[3/5] w-full flex-col overflow-hidden rounded-xl bg-[var(--od-card)] shadow-md cursor-pointer md:aspect-[3/4]"
      onClick={() => onPreview?.(thread)}
      scale={1.02}
      y={-4}
    >
      {/* Background Image Layer (Parallax Target) */}
      <div
        ref={imageLayerRef}
        className="absolute inset-[-10%] z-0 h-[120%] w-[120%] bg-[var(--od-bg-tertiary)] transition-transform duration-100 ease-out will-change-transform"
      >
        {thread.thumbnail_urls && thread.thumbnail_urls.length > 0 ? (
          <MultiImageGrid
            images={thread.thumbnail_urls}
            alt={thread.title}
            className="h-full w-full object-cover"
          />
        ) : thread.thumbnail_url ? (
          <MultiImageGrid
            images={[thread.thumbnail_url]}
            alt={thread.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-[var(--od-bg-secondary)]">
            <ImageIcon className="h-12 w-12 text-[var(--od-bg-tertiary)] opacity-50" />
          </div>
        )}
      </div>

      {/* Gradient Overlay - Only show for threads with images to ensure text readability */}
      {hasThumbnail && (
        <div className="absolute inset-0 z-10 bg-gradient-to-t from-black/90 via-black/40 to-transparent pointer-events-none" />
      )}

      {/* Top Right Actions */}
      <div className="absolute right-2 top-2 z-20 flex flex-col items-end gap-2 opacity-100 transition-opacity duration-200 md:opacity-0 md:group-hover:opacity-100">
        {/* Refresh Button */}
        <button
          onClick={handleRefreshImage}
          disabled={isRefreshing}
          className={`flex h-8 w-8 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur-md transition-colors hover:bg-black/60 ${isRefreshing ? 'cursor-wait' : ''
            }`}
          title="刷新封面图"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>

        {/* Thread Actions */}
        <ThreadActions
          threadId={thread.thread_id}
          guildId={thread.guild_id}
          variant="glass"
        />
      </div>

      {/* Status Badges */}
      <ThreadStatusBadges
        isFollowing={thread.is_following}
        hasUpdate={thread.has_update}
        variant="card"
      />

      {/* Bottom Content Area */}
      <div className={`absolute bottom-0 left-0 right-0 z-20 flex flex-col p-3 ${hasThumbnail ? 'text-white' : 'text-[var(--od-text-primary)]'}`}>

        {/* Tags */}
        {thread.tags && thread.tags.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {thread.tags.slice(0, 3).map((tag) => (
              <button
                key={tag}
                onClick={(e) => {
                  e.stopPropagation();
                  onTagClick?.(tag);
                }}
                className={`rounded-md px-2 py-0.5 text-[10px] font-medium backdrop-blur-sm transition-colors border ${hasThumbnail
                  ? 'bg-white/20 text-white hover:bg-white/30 border-white/10'
                  : 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-secondary)] border-[var(--od-border)]'
                  }`}
              >
                {tag}
              </button>
            ))}
            {/* Show +N for explicit tags */}
            {thread.tags.length > 3 && (
              <span className={`rounded-md px-2 py-0.5 text-[10px] backdrop-blur-sm border ${hasThumbnail
                ? 'bg-white/20 text-white border-white/10'
                : 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)] border-[var(--od-border)]'
                }`}>
                +{thread.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Title */}
        <h3 className={`mb-2 line-clamp-2 text-sm font-bold leading-snug drop-shadow-md md:text-base ${hasThumbnail ? 'text-white' : 'text-[var(--od-text-primary)]'}`}>
          <HighlightText text={thread.title} highlight={searchQuery} className={hasThumbnail ? 'text-white' : 'text-[var(--od-text-primary)]'} />
        </h3>

        {/* Footer: Author & Stats */}
        <div className={`flex items-center justify-between border-t pt-2 text-xs ${hasThumbnail ? 'border-white/10 text-white/80' : 'border-[var(--od-border)] text-[var(--od-text-secondary)]'}`}>

          {/* Author Info */}
          <div className="flex items-center gap-2 overflow-hidden">
            <AuthorAvatar author={thread.author} className="h-5 w-5 ring-1 ring-white/20" />
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (authorName && onAuthorClick) {
                  onAuthorClick(authorName);
                }
              }}
              className={`truncate font-medium hover:underline max-w-[100px] ${hasThumbnail ? 'hover:text-white' : 'hover:text-[var(--od-text-primary)]'}`}
            >
              {authorName}
            </button>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="flex items-center gap-1">
              <MessageCircle className="h-3.5 w-3.5 opacity-80" />
              {thread.reply_count}
            </span>
            <span className="flex items-center gap-1">
              <ThumbsUp className="h-3.5 w-3.5 opacity-80" />
              {thread.reaction_count}
            </span>
          </div>
        </div>
      </div>
    </MotionWrapper>
  );
}
