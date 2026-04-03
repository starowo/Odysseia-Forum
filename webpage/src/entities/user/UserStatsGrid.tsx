interface UserStatItem {
  label: string;
  value: number | string;
}

interface UserStatsGridProps {
  items: UserStatItem[];
}

export function UserStatsGrid({ items }: UserStatsGridProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-3">
          <p className="text-xs text-[var(--od-text-tertiary)]">{item.label}</p>
          <p className="mt-1 text-xl font-bold text-[var(--od-text-primary)]">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
