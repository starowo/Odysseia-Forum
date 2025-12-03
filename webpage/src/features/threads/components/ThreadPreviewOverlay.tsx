import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { MarkdownText } from '@/components/common/MarkdownText';
import { LazyImage } from '@/components/common/LazyImage';
import type { Thread } from '@/types/thread.types';
import { getAvatarUrl } from '@/lib/utils/discord';

export interface ThreadPreviewOverlayProps {
  thread: Thread;
  onClose: () => void;
  externalUrlOverride?: string | null;
  hideExternalButton?: boolean;
}

/**
 * 帖子预览上浮浮层：
 * - 居中放大展示帖子卡片；
 * - 支持 Markdown、长文本和独立滚动区域；
 * - 保留「在 Discord 中打开」按钮。
 */
export function ThreadPreviewOverlay({
  thread,
  onClose,
  externalUrlOverride,
  hideExternalButton,
}: ThreadPreviewOverlayProps) {
  // visible 用于控制「刚挂载时从 0 → 1」的入场动画
  const [visible, setVisible] = useState(false);
  const [closing, setClosing] = useState(false);

  // 挂载后下一帧再标记为可见，触发淡入+缩放动画
  useEffect(() => {
    const id = window.setTimeout(() => {
      setVisible(true);
    }, 0);
    return () => window.clearTimeout(id);
  }, []);

  const handleStartClose = () => {
    if (closing) return;
    setClosing(true);
    setVisible(false);
    // 等待动画结束再真正卸载
    window.setTimeout(() => {
      onClose();
    }, 220);
  };

  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';

  // 构建 Discord 帖子链接（与 ThreadCard 保持一致）
  const guildId = thread.guild_id || import.meta.env.VITE_GUILD_ID || '@me';
  const defaultDiscordUrl = thread.channel_id
    ? `https://discord.com/channels/${guildId}/${thread.channel_id}/${thread.thread_id}`
    : null;

  const externalUrl = externalUrlOverride === undefined ? defaultDiscordUrl : externalUrlOverride;

  // 使用 Portal 将浮层挂到 body 下，避免被侧边栏等容器裁剪
  if (typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div
      className={`fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm px-3 sm:px-6 transition-opacity duration-250 ${closing || !visible ? 'opacity-0' : 'opacity-100'
        }`}
      onClick={handleStartClose}
    >
      <div
        className={`relative my-4 flex w-full max-w-4xl h-[85vh] flex-col overflow-hidden rounded-xl bg-[var(--od-card)] shadow-2xl sm:my-6 sm:rounded-2xl transform transition-all duration-250 ease-out ${closing || !visible
          ? 'scale-95 translate-y-4 opacity-0'
          : 'scale-100 translate-y-0 opacity-100'
          }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          type="button"
          onClick={handleStartClose}
          className="absolute right-3 top-3 z-10 rounded-full bg-black/60 p-1.5 text-xs text-white shadow-md hover:bg-black/80"
          aria-label="关闭预览"
        >
          <X className="h-4 w-4" />
        </button>

        {/* 顶部大图 / 轮播 */}
        <div className="relative h-[45%] w-full flex-shrink-0 overflow-hidden bg-[var(--od-bg-tertiary)] group/carousel">
          {thread.thumbnail_urls && thread.thumbnail_urls.length > 0 ? (
            <Carousel images={thread.thumbnail_urls} alt={thread.title} />
          ) : thread.thumbnail_url ? (
            <LazyImage
              src={thread.thumbnail_url}
              alt={thread.title}
              className="h-full w-full bg-black object-contain"
            />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-[#18191c] to-[#1e1f22]" />
          )}

          {thread.has_update && (
            <div className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-[#23a55a]/90 px-2.5 py-0.5 text-xs font-semibold text-white shadow-sm backdrop-blur-sm z-20">
              <span className="inline-block h-2 w-2 rounded-full bg-white animate-[pulse_2.4s_ease-in-out_infinite]" />
              <span>有更新</span>
            </div>
          )}
        </div>

        {/* 正文区域 - 独立滚动 */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {/* 标题 */}
          <h2 className="mb-3 text-lg font-bold leading-snug text-[var(--od-text-primary)] sm:text-xl">
            {thread.is_following && (
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[#f23f43]" />
            )}
            {thread.title}
          </h2>

          {/* 作者信息 */}
          <div className="mb-3 flex items-center gap-2 text-xs text-[var(--od-text-tertiary)] sm:text-sm">
            {/* 头像 */}
            <div className="relative h-6 w-6 flex-shrink-0 overflow-hidden rounded-full bg-[var(--od-bg-tertiary)]">
              <LazyImage
                src={
                  thread.author?.avatar_url ||
                  (thread.author?.id
                    ? getAvatarUrl({
                      id: thread.author.id,
                      avatar: thread.author.avatar,
                    })
                    : 'https://cdn.discordapp.com/embed/avatars/0.png')
                }
                alt={authorName}
                className="h-full w-full object-cover"
              />
            </div>

            <span className="font-medium text-[var(--od-link)]">{authorName}</span>
            {thread.channel_id && (
              <>
                <span>·</span>
                <span>频道 {thread.channel_id}</span>
              </>
            )}
          </div>

          {/* 标签 */}
          {thread.tags && thread.tags.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-2">
              {thread.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-md bg-[var(--od-bg-secondary)] px-2.5 py-1 text-xs font-medium text-[var(--od-text-secondary)]"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* 正文 Markdown */}
          {thread.first_message_excerpt && thread.first_message_excerpt.trim() !== '...' ? (
            <div className="od-md text-sm text-[var(--od-text-primary)]">
              <MarkdownText text={thread.first_message_excerpt} />
            </div>
          ) : (
            <p className="mt-2 text-sm text-[var(--od-text-tertiary)]">
              当前接口只返回首条消息的摘要，完整内容请在 Discord 中查看。
            </p>
          )}

          {/* 打开原帖按钮（静态通知可选择隐藏） */}
          {!hideExternalButton && externalUrl && (
            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => window.open(externalUrl, '_blank', 'noopener,noreferrer')}
                className="rounded-lg bg-[var(--od-accent)] px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:scale-105 hover:bg-[var(--od-accent-hover)]"
              >
                在 Discord 中打开
              </button>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

function Carousel({ images, alt }: { images: string[]; alt: string }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const next = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev + 1) % images.length);
  };

  const prev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  const goTo = (index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex(index);
  };

  if (images.length === 0) return null;
  if (images.length === 1) {
    return (
      <LazyImage
        src={images[0]}
        alt={alt}
        className="h-full w-full bg-black object-contain"
      />
    );
  }

  return (
    <div className="relative h-full w-full">
      {/* Slides */}
      <div className="h-full w-full relative">
        {images.map((src, idx) => (
          <div
            key={idx}
            className={`absolute inset-0 transition-opacity duration-300 ${idx === currentIndex ? 'opacity-100 z-10' : 'opacity-0 z-0'
              }`}
          >
            <LazyImage
              src={src}
              alt={`${alt} ${idx + 1}`}
              className="h-full w-full bg-black object-contain"
            />
          </div>
        ))}
      </div>

      {/* Controls */}
      <button
        onClick={prev}
        className="absolute left-2 top-1/2 -translate-y-1/2 z-30 rounded-full bg-black/50 p-1.5 text-white transition-colors hover:bg-black/70 pointer-events-auto"
      >
        <ChevronLeft className="h-6 w-6" />
      </button>
      <button
        onClick={next}
        className="absolute right-2 top-1/2 -translate-y-1/2 z-30 rounded-full bg-black/50 p-1.5 text-white transition-colors hover:bg-black/70 pointer-events-auto"
      >
        <ChevronRight className="h-6 w-6" />
      </button>

      {/* Indicators */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20 flex gap-1.5">
        {images.map((_, idx) => (
          <button
            key={idx}
            onClick={(e) => goTo(idx, e)}
            className={`h-1.5 rounded-full transition-all ${idx === currentIndex ? 'w-4 bg-white' : 'w-1.5 bg-white/50 hover:bg-white/80'
              }`}
          />
        ))}
      </div>

      {/* Counter */}
      <div className="absolute bottom-3 right-3 z-20 rounded-full bg-black/50 px-2 py-0.5 text-xs text-white backdrop-blur-sm">
        {currentIndex + 1} / {images.length}
      </div>
    </div>
  );
}