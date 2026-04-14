import { Outlet, useLocation } from 'react-router-dom';
import { ResizableSidebar } from '@/widgets/sidebar/ResizableSidebar';
import { AppSidebar } from '@/widgets/layout/AppSidebar';
import { TopBar } from '@/widgets/layout/TopBar';
import { MobileTabBar } from '@/widgets/layout/MobileTabBar';
import { MascotBar } from '@/features/mascot/components/MascotBar';
import { GlobalThreadPreview } from '@/widgets/thread-preview/GlobalThreadPreview';
import { useSidebarCollapsedSetting, useSettings } from '@/shared/hooks/useSettings';
import { useEffect, useState } from 'react';

/**
 * AppShell — 全站布局骨架
 *
 * 采用 h-screen + overflow-hidden 的"应用壳"模式：
 *   ┌──────────────────────────────────────────┐
 *   │  Sidebar  │  TopBar                       │
 *   │           │  ┌───────────────────────────┐│
 *   │           │  │ MainScrollArea (Outlet)   ││
 *   │  (PC端)   │  │                           ││
 *   │           │  │                           ││
 *   │           │  └───────────────────────────┘│
 *   └──────────────────────────────────────────┘
 *   [  移动端底部 Tab 栏  ] (md:hidden)
 *
 * 布局模式可通过 useSettings 或将来的 useLayoutStore 控制：
 *   - sidebarCollapsed: 侧边栏收起
 *   - 未来: topBarVisible / immersiveMode 等
 */
export function RootLayout() {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const sidebarCollapsed = useSidebarCollapsedSetting();
  const { updateSettings } = useSettings();
  const location = useLocation();

  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname, location.search, location.hash]);

  return (
    <div className="od-app-shell relative flex h-screen w-full overflow-hidden text-[var(--od-text-primary)]">
      <div className="pointer-events-none absolute inset-0 z-0 od-shell-surface" />

      <div className="od-operation-base pointer-events-none absolute inset-0 z-[5]" />

      {/* ── Sidebar (桌面端固定 / 移动端抽屉) ── */}
        <ResizableSidebar
          isMobileOpen={isMobileOpen}
          setIsMobileOpen={setIsMobileOpen}
          isCollapsed={sidebarCollapsed}
          setIsCollapsed={(collapsed: boolean) => updateSettings({ sidebarCollapsed: collapsed })}
        >
          <AppSidebar />
      </ResizableSidebar>

      {/* TopBar 与 Sidebar 处于同一操作层 */}
      <TopBar
        onMenuClick={() => setIsMobileOpen(true)}
        sidebarCollapsed={sidebarCollapsed}
      />

      {/* ── 主内容列 ── */}
      <div
        className={`relative z-10 flex min-w-0 flex-1 flex-col transition-[margin] duration-300 ${
          sidebarCollapsed ? 'lg:ml-0' : 'lg:ml-[170px]'
        }`}
      >
        {/* 主滚动区 — 圆角面板 + 独立背景色，形成视觉层级 */}
        <div className="od-content-surface relative z-10 mt-[3.25rem] flex-1 min-h-0 sm:mt-[4.25rem] sm:rounded-tl-[2.5rem] sm:overflow-hidden">
          {/* 顶部高光渐变装饰 */}
          <div className="pointer-events-none absolute left-0 right-0 top-0 z-0 hidden h-24 rounded-tl-[2.5rem] bg-gradient-to-b from-white/[0.02] to-transparent sm:block" />
          <main
            id="main-scroll-container"
            className="relative z-10 h-full overflow-y-auto scroll-smooth pb-20 md:pb-0"
          >
            <Outlet />
          </main>
        </div>
      </div>

      {/* ── 移动端底部 Tab 栏 ── */}
      <MobileTabBar />

      {/* ── 全局辅助层 ── */}
      <GlobalThreadPreview />
      <MascotBar />
    </div>
  );
}
