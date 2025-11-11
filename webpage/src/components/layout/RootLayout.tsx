import { Outlet } from 'react-router-dom';
import { DevNav } from '@/components/DevNav';

export function RootLayout() {
  return (
    <div className="min-h-screen bg-slate-950">
      <Outlet />
      <DevNav />
    </div>
  );
}
