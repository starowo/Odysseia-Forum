import { Outlet } from 'react-router-dom';
import { DevNav } from '@/components/DevNav';

const isDevToolsEnabled = import.meta.env.DEV || import.meta.env.VITE_API_MOCKING === 'true';

export function RootLayout() {
  return (
    <div className="min-h-screen bg-[var(--od-bg)] text-[var(--od-text-primary)]">
      <Outlet />
      {isDevToolsEnabled && <DevNav />}
    </div>
  );
}
