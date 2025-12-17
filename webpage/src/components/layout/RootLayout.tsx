import { Outlet } from 'react-router-dom';
import { MascotBar } from '@/features/mascot/components/MascotBar';
import { ScrollToTop } from '@/components/common/ScrollToTop';

export function RootLayout() {
  return (
    <div className="min-h-screen bg-[var(--od-bg)] text-[var(--od-text-primary)]">
      <Outlet />
      <MascotBar />
      <ScrollToTop />
    </div>
  );
}
