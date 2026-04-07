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
