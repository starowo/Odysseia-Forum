import type { ComponentType } from 'react';

interface UserStatItem {
  label: string;
  value: number | string;
  icon?: ComponentType<{ className?: string }>;
}

interface UserStatsGridProps {
  items: UserStatItem[];
}

export function UserStatsGrid({ items }: UserStatsGridProps) {
  return (
    <div className="mx-auto grid max-w-4xl grid-cols-2 gap-x-3 gap-y-4 sm:gap-x-4 sm:gap-y-7 lg:grid-cols-4 lg:gap-x-5">
      {items.map((item) => (
        <div key={item.label} className="py-1 text-center sm:py-2">
          {item.icon && (
            <div className="mb-1.5 flex justify-center text-[var(--od-accent)] sm:mb-3">
              <item.icon className="h-4 w-4 sm:h-4.5 sm:w-4.5" />
            </div>
          )}
          <div>
            <p className="text-[0.78rem] font-medium text-[var(--od-text-secondary)] sm:text-sm">{item.label}</p>
            <p className="mt-1 text-[1.55rem] font-bold tracking-[-0.04em] text-[var(--od-text-value)] tabular-nums sm:mt-2 sm:text-[2.5rem]">
              {item.value}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
