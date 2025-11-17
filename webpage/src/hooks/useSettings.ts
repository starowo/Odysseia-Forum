import { useState, useEffect } from 'react';
import { getUserSettings, saveUserSettings, type UserSettings } from '@/lib/settings';

export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>(getUserSettings);

  useEffect(() => {
    // 监听设置变化事件
    const handleSettingsChange = (event: CustomEvent<UserSettings>) => {
      setSettings(event.detail);
    };

    window.addEventListener('settingsChanged', handleSettingsChange as EventListener);
    
    return () => {
      window.removeEventListener('settingsChanged', handleSettingsChange as EventListener);
    };
  }, []);

  const updateSettings = (updates: Partial<UserSettings>) => {
    const newSettings = { ...settings, ...updates };
    setSettings(newSettings);
    saveUserSettings(newSettings);
  };

  return {
    settings,
    updateSettings,
  };
}
