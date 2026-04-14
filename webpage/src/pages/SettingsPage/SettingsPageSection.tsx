import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

import { FluidDivider } from '@/shared/ui/FluidDivider';

type SettingsPageSectionProps = {
  dividerLabel: string;
  kicker: string;
  title: string;
  icon: LucideIcon;
  children: ReactNode;
};

export function SettingsPageSection({
  dividerLabel,
  kicker,
  title,
  icon: Icon,
  children,
}: SettingsPageSectionProps) {
  return (
    <section className="od-setting-section">
      <FluidDivider label={dividerLabel} tone="strong" className="mb-5" />
      <div className="mb-4 flex items-center gap-3">
        <Icon className="od-choice-icon h-5 w-5 text-[var(--od-text-secondary)]" />
        <div>
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">
            {kicker}
          </p>
          <h2 className="od-section-title mt-1">{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}
