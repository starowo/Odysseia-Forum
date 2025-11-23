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
    // 直接从 localStorage 读取最新的设置，而不是依赖当前组件的 state
    const currentSettings = getUserSettings();
    const newSettings = { ...currentSettings, ...updates };
    // setSettings(newSettings); // 不再需要立即更新当前组件，让事件去处理
    saveUserSettings(newSettings); // saveUserSettings 会广播事件，让所有组件统一更新
  };

  return {
    settings,
    updateSettings,
  };
}
