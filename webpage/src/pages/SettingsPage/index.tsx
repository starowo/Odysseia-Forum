import { useEffect, useState } from 'react';

import { useSettings } from '@/shared/hooks/useSettings';
import { resetUserSettings } from '@/shared/lib/settings';
import { notifyError, notifySuccess } from '@/shared/lib/notify';

import { AdvancedSettingsSection } from './AdvancedSettingsSection';
import { AtmosphereSettingsSection } from './AtmosphereSettingsSection';
import { DisplaySettingsSection } from './DisplaySettingsSection';
import { NotificationsSettingsSection } from './NotificationsSettingsSection';
import { SettingsPageHeader } from './SettingsPageHeader';
import { VersionSettingsSection } from './VersionSettingsSection';

export function SettingsPage() {
  const { settings, updateSettings } = useSettings();
  const [opacityDraft, setOpacityDraft] = useState(Math.round(settings.backgroundImageOpacity * 100));
  const [blurDraft, setBlurDraft] = useState(Math.round(settings.glassBlur));

  useEffect(() => {
    setOpacityDraft(Math.round(settings.backgroundImageOpacity * 100));
  }, [settings.backgroundImageOpacity]);

  useEffect(() => {
    setBlurDraft(Math.round(settings.glassBlur));
  }, [settings.glassBlur]);

  const handleUploadBackground = (file: File | null) => {
    if (!file) return;

    const maxBytes = 5 * 1024 * 1024;
    if (file.size > maxBytes) {
      notifyError('图片超过 5MB，无法保存到本地');
      return;
    }

    if (!file.type.startsWith('image/')) {
      notifyError('仅支持图片文件');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : '';
      if (!result.startsWith('data:image/')) {
        notifyError('图片读取失败，请重试');
        return;
      }

      if (result.length > 4_500_000) {
        notifyError('base64 体积过大，建议改用 URL 或内置背景图');
        return;
      }

      try {
        updateSettings({
          backgroundImageBase64: result,
          backgroundImageUrl: '',
          backgroundImageEnabled: true,
        });
        notifySuccess('本地背景图已保存（base64）');
      } catch {
        notifyError('保存失败，可能是本地存储空间不足');
      }
    };
    reader.onerror = () => notifyError('读取图片失败');
    reader.readAsDataURL(file);
  };

  const handleClearBackgroundImage = () => {
    updateSettings({
      backgroundImageEnabled: false,
      backgroundImageUrl: '',
      backgroundImageBase64: '',
    });
    notifySuccess('背景图已清除');
  };

  const handleResetSettings = () => {
    if (confirm('确定要重置所有设置为默认值吗？')) {
      resetUserSettings();
      notifySuccess('设置已重置为默认值');
      setTimeout(() => window.location.reload(), 1000);
    }
  };

  const commitOpacity = () => updateSettings({ backgroundImageOpacity: opacityDraft / 100 });
  const commitBlur = () => updateSettings({ glassBlur: blurDraft });

  return (
    <div className="px-4 py-4 text-[var(--od-text-primary)] sm:px-6 lg:px-8">
      <SettingsPageHeader />

      <div className="mt-4 space-y-10 px-1">
        <DisplaySettingsSection settings={settings} updateSettings={updateSettings} />

        <AtmosphereSettingsSection
          settings={settings}
          opacityDraft={opacityDraft}
          blurDraft={blurDraft}
          onOpacityDraftChange={setOpacityDraft}
          onBlurDraftChange={setBlurDraft}
          onCommitOpacity={commitOpacity}
          onCommitBlur={commitBlur}
          onUploadBackground={handleUploadBackground}
          onClearBackgroundImage={handleClearBackgroundImage}
          updateSettings={updateSettings}
        />

        <NotificationsSettingsSection settings={settings} updateSettings={updateSettings} />
        <AdvancedSettingsSection onResetSettings={handleResetSettings} />
        <VersionSettingsSection />

        <div className="rounded-[1.3rem] bg-[color-mix(in_oklab,var(--od-accent)_8%,transparent)] p-4">
          <p className="text-sm text-[var(--od-text-secondary)]">
            💡 <span className="font-medium text-[var(--od-text-primary)]">小提醒：</span>
            你的设置都保存在本地浏览器里。清除浏览器数据的话，这些设置也会一起消失。
          </p>
        </div>
      </div>
    </div>
  );
}
