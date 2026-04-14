import { Info } from 'lucide-react';

import { APP_VERSION } from '@/shared/config/appInfo';

import { SettingsPageSection } from './SettingsPageSection';

export function VersionSettingsSection() {
  return (
    <SettingsPageSection dividerLabel="Version" kicker="Release Notes" title="版本与更新" icon={Info}>
      <p className="text-sm text-[var(--od-text-secondary)]">
        当前前端版本：
        <span className="ml-1 font-mono text-[var(--od-text-emphasis)]">{APP_VERSION}</span>
      </p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-[var(--od-text-tertiary)]">
        <li>新增帖子预览浮层与 Markdown 展示体验</li>
        <li>改进搜索筛选与列表/网格视图切换</li>
        <li>优化登出、Mock 环境与错误提示的健壮性</li>
      </ul>
    </SettingsPageSection>
  );
}
