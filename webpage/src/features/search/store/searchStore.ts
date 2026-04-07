/**
 * useSearchStore — 精简后的搜索 UI 状态
 *
 * V2 重构后，此 Store 只保留少量纯 UI 状态：
 *   - Banner 可见性和轮播数据（供 FloatingBanner 使用）
 *
 * 以下状态已迁移：
 *   - 搜索条件（query, channel, sort, tags, page, perPage） → URL searchParams
 *   - 帖子预览（previewThread, previewThreadId, previewOptions） → previewStore
 */

import { create } from 'zustand';

interface SearchUIState {
  // Banner UI 状态
  isMainBannerVisible: boolean;
  activeBannerId: string | null;

  // Actions
  setMainBannerVisible: (visible: boolean) => void;
  setActiveBannerId: (bannerId: string | null) => void;
}

export const useSearchStore = create<SearchUIState>()((set, get) => ({
  isMainBannerVisible: true,
  activeBannerId: null,

  setMainBannerVisible: (visible) => {
    if (get().isMainBannerVisible === visible) return;
    set({ isMainBannerVisible: visible });
  },

  setActiveBannerId: (bannerId) => {
    if (get().activeBannerId === bannerId) return;
    set({ activeBannerId: bannerId });
  },
}));
