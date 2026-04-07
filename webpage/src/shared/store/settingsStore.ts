import { create } from 'zustand';

import {
  getUserSettings,
  saveUserSettings,
  type UserSettings,
} from '@/shared/lib/settings';

interface SettingsState {
  settings: UserSettings;
  updateSettings: (updates: Partial<UserSettings>) => void;
  resetSettingsState: (nextSettings?: UserSettings) => void;
}

const readInitialSettings = (): UserSettings => {
  if (typeof window === 'undefined') {
    return getUserSettings();
  }

  return getUserSettings();
};

export const useSettingsStore = create<SettingsState>()((set, get) => ({
  settings: readInitialSettings(),

  updateSettings: (updates) => {
    const nextSettings = { ...get().settings, ...updates };
    saveUserSettings(nextSettings);
    set({ settings: nextSettings });
  },

  resetSettingsState: (nextSettings) => {
    set({ settings: nextSettings ?? readInitialSettings() });
  },
}));
