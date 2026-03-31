/**
 * usePreviewStore — 帖子预览独立状态
 *
 * 从 searchStore 中抽离，使"帖子预览"和"搜索条件"彻底解耦。
 * 消费者：GlobalThreadPreview, FloatingBanner, NotificationCenter, SearchPage, FollowsPage
 */

import { create } from 'zustand';
import type { Thread } from '@/entities/thread/types';

interface PreviewOptions {
  externalUrlOverride?: string | null;
  hideExternalButton?: boolean;
}

interface PreviewState {
  /** 直接传入的完整 Thread 对象（用于已加载过的帖子） */
  previewThread: Thread | null;
  /** 仅传入 ID，由 GlobalThreadPreview 按需拉取详情 */
  previewThreadId: string | null;
  /** 预览面板的附加选项 */
  previewOptions: PreviewOptions;

  /** 用完整 Thread 对象打开预览 */
  setPreviewThread: (
    thread: Thread | null,
    options?: PreviewOptions,
  ) => void;
  /** 用 Thread ID 打开预览（延迟加载） */
  setPreviewThreadId: (
    id: string | null,
    options?: PreviewOptions,
  ) => void;
}

export const usePreviewStore = create<PreviewState>()((set) => ({
  previewThread: null,
  previewThreadId: null,
  previewOptions: {},

  setPreviewThread: (thread, options) =>
    set({
      previewThread: thread,
      previewThreadId: null,
      previewOptions: options || {},
    }),

  setPreviewThreadId: (id, options) =>
    set({
      previewThreadId: id,
      previewThread: null,
      previewOptions: options || {},
    }),
}));
