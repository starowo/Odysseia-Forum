import { Outlet } from 'react-router-dom';
import { DevNav } from '@/components/DevNav';

export function RootLayout() {
  return (
    <div className="min-h-screen bg-[var(--od-bg)] text-[var(--od-text-primary)]">
      <Outlet />
      <DevNav />
    </div>
  );
}
