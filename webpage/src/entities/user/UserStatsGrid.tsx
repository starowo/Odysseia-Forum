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
        <div key={item.label} className="od-fluid-panel rounded-xl p-3">
          <p className="od-text-meta">{item.label}</p>
          <p className="mt-1 text-[1.55rem] font-od-bold text-[var(--od-text-value)] tabular-nums">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
