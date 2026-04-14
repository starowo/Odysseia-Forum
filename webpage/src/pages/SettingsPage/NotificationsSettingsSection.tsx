import { Bell } from 'lucide-react';

import type { UserSettings } from '@/shared/lib/settings';

import { SettingsPageSection } from './SettingsPageSection';
import { SettingsToggle } from './SettingsToggle';

type NotificationsSettingsSectionProps = {
  settings: UserSettings;
  updateSettings: (updates: Partial<UserSettings>) => void;
};

export function NotificationsSettingsSection({ settings, updateSettings }: NotificationsSettingsSectionProps) {
  return (
    <SettingsPageSection dividerLabel="Notifications" kicker="Signals" title="通知" icon={Bell}>
      <div className="space-y-3">
        <div className="od-setting-row">
          <div>
            <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">新帖通知</p>
            <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">关注的频道有新帖了，我会第一时间告诉你。</p>
          </div>
          <SettingsToggle
            checked={settings.notifications.newPosts}
            onToggle={() => updateSettings({ notifications: { ...settings.notifications, newPosts: !settings.notifications.newPosts } })}
            ariaLabel="切换新帖通知"
          />
        </div>

        <div className="od-setting-row">
          <div>
            <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">回复通知</p>
            <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">有人回复了你的帖子，我会提醒你过去看看。</p>
          </div>
          <SettingsToggle
            checked={settings.notifications.replies}
            onToggle={() => updateSettings({ notifications: { ...settings.notifications, replies: !settings.notifications.replies } })}
            ariaLabel="切换回复通知"
          />
        </div>

        <div className="od-setting-row">
          <div>
            <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">提及通知</p>
            <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">有人 @ 了你，可能在找你聊天哦。</p>
          </div>
          <SettingsToggle
            checked={settings.notifications.mentions}
            onToggle={() => updateSettings({ notifications: { ...settings.notifications, mentions: !settings.notifications.mentions } })}
            ariaLabel="切换提及通知"
          />
        </div>
      </div>
    </SettingsPageSection>
  );
}
