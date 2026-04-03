import { Outlet } from 'react-router-dom';
import { ResizableSidebar } from '@/widgets/sidebar/ResizableSidebar';
import { AppSidebar } from '@/widgets/layout/AppSidebar';
import { TopBar } from '@/widgets/layout/TopBar';
import { MobileTabBar } from '@/widgets/layout/MobileTabBar';
import { MascotBar } from '@/features/mascot/components/MascotBar';
import { GlobalThreadPreview } from '@/widgets/thread-preview/GlobalThreadPreview';
import { useSettings } from '@/shared/hooks/useSettings';
import { useState } from 'react';

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
  const { settings, updateSettings } = useSettings();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[var(--od-bg)] text-[var(--od-text-primary)]">
      {/* ── Sidebar (桌面端固定 / 移动端抽屉) ── */}
      <ResizableSidebar
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
        isCollapsed={settings.sidebarCollapsed}
        setIsCollapsed={(collapsed: boolean) => updateSettings({ sidebarCollapsed: collapsed })}
      >
        <AppSidebar />
      </ResizableSidebar>

      {/* ── 主内容列 ── */}
      <div
        className={`flex min-w-0 flex-1 flex-col transition-all duration-300 ${
          settings.sidebarCollapsed ? 'lg:ml-0' : 'lg:ml-[170px]'
        }`}
      >
        {/* TopBar：与侧边栏背景融合，无独立背景和边框 */}
        <TopBar onMenuClick={() => setIsMobileOpen(true)} />

        {/* 主滚动区 — 圆角面板 + 独立背景色，形成视觉层级 */}
        <main
          id="main-scroll-container"
          className="relative flex-1 overflow-y-auto scroll-smooth bg-[var(--od-bg-secondary)] pb-20 sm:rounded-tl-[2.5rem] sm:border-l sm:border-t sm:border-white/[0.06] md:pb-0"
        >
          {/* 顶部高光渐变装饰 */}
          <div className="pointer-events-none absolute left-0 right-0 top-0 z-0 hidden h-32 rounded-tl-[2.5rem] bg-gradient-to-b from-white/[0.02] to-transparent sm:block" />
          <div className="relative z-10">
            <Outlet />
          </div>
        </main>
      </div>

      {/* ── 移动端底部 Tab 栏 ── */}
      <MobileTabBar />

      {/* ── 全局辅助层 ── */}
      <GlobalThreadPreview />
      <MascotBar />
    </div>
  );
}
