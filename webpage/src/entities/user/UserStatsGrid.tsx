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
    <div className="mx-auto grid max-w-4xl gap-x-4 gap-y-7 sm:grid-cols-2 lg:grid-cols-4 lg:gap-x-5">
      {items.map((item) => (
        <div key={item.label} className="py-1 text-center">
          {item.icon && (
            <div className="mb-3 flex justify-center text-[var(--od-accent)]">
              <item.icon className="h-4.5 w-4.5" />
            </div>
          )}
          <div>
            <p className="text-sm font-medium text-[var(--od-text-secondary)]">{item.label}</p>
            <p className="mt-2 text-[2.3rem] font-bold tracking-[-0.04em] text-[var(--od-text-value)] tabular-nums sm:text-[2.5rem]">
              {item.value}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
