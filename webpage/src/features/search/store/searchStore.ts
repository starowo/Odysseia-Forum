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
  activeBanner: { id: string; image: string; title: string; description: string } | null;
  bannerList: { id: string; image: string; title: string; description: string }[];

  // Actions
  setMainBannerVisible: (visible: boolean) => void;
  setActiveBanner: (banner: { id: string; image: string; title: string; description: string } | null) => void;
  setBannerList: (banners: { id: string; image: string; title: string; description: string }[]) => void;
}

export const useSearchStore = create<SearchUIState>()((set, get) => ({
  isMainBannerVisible: true,
  activeBanner: null,
  bannerList: [],

  setMainBannerVisible: (visible) => {
    if (get().isMainBannerVisible === visible) return;
    set({ isMainBannerVisible: visible });
  },

  setActiveBanner: (banner) => {
    const current = get().activeBanner;
    if (JSON.stringify(current) === JSON.stringify(banner)) return;
    set({ activeBanner: banner });
  },

  setBannerList: (list) => {
    const current = get().bannerList;
    if (JSON.stringify(current) === JSON.stringify(list)) return;
    set({ bannerList: list });
  },
}));
