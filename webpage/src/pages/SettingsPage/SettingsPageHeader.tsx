import { Settings } from 'lucide-react';

export function SettingsPageHeader() {
  return (
    <div className="px-1 py-3">
      <div className="flex items-center gap-4">
        <Settings className="h-6 w-6 shrink-0 text-[var(--od-accent)]" />
        <div>
          <p className="mb-2 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">
            Personal Workspace
          </p>
          <h1 className="od-section-title">设置</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)]">
            这里是你的专属调色板，我帮你把显示、氛围和提醒都重新分了类。调完立刻生效，阅读节奏会清楚很多。
          </p>
        </div>
      </div>
    </div>
  );
}
