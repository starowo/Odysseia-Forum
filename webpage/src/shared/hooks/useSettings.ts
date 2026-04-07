import { useCallback } from 'react';

import { useSettingsStore } from '@/shared/store/settingsStore';
import type { UserSettings } from '@/shared/lib/settings';

export function useSettings() {
  const settings = useSettingsStore((state) => state.settings);
  const storeUpdateSettings = useSettingsStore((state) => state.updateSettings);

  const updateSettings = useCallback(
    (updates: Partial<UserSettings>) => {
      storeUpdateSettings(updates);
    },
    [storeUpdateSettings],
  );

  return {
    settings,
    updateSettings,
  };
}

export function useLayoutMode() {
  return useSettingsStore((state) => state.settings.layoutMode);
}

export function useFontSizeSetting() {
  return useSettingsStore((state) => state.settings.fontSize);
}

export function useCardSizeSetting() {
  return useSettingsStore((state) => state.settings.cardSize);
}

export function useCardGridClass() {
  const cardSize = useCardSizeSetting();
  if (cardSize === 'large') {
    return 'grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
  }
  if (cardSize === 'compact') {
    return 'grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5';
  }
  return 'grid grid-cols-2 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
}

export function useImageModeSetting() {
  return useSettingsStore((state) => state.settings.imageMode);
}

export function useOpenModeSetting() {
  return useSettingsStore((state) => state.settings.openMode);
}

export function useSidebarCollapsedSetting() {
  return useSettingsStore((state) => state.settings.sidebarCollapsed);
}

export function useThemeSettings() {
  return useSettingsStore((state) => ({
    theme: state.settings.theme,
    fontMode: state.settings.fontMode,
    glassBlur: state.settings.glassBlur,
    backgroundImageBase64: state.settings.backgroundImageBase64,
    backgroundImageUrl: state.settings.backgroundImageUrl,
    backgroundImageEnabled: state.settings.backgroundImageEnabled,
    backgroundImageOpacity: state.settings.backgroundImageOpacity,
    glassMode: state.settings.glassMode,
    backgroundlessMode: state.settings.backgroundlessMode,
  }));
}
