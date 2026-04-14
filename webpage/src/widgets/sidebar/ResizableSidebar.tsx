import { ReactNode } from 'react';
import { X, ChevronLeft } from 'lucide-react';

interface ResizableSidebarProps {
  children: ReactNode;
  isMobileOpen?: boolean;
  setIsMobileOpen?: (open: boolean) => void;
  isCollapsed?: boolean;
  setIsCollapsed?: (collapsed: boolean) => void;
}

export function ResizableSidebar({
  children,
  isMobileOpen = false,
  setIsMobileOpen,
  isCollapsed = false,
  setIsCollapsed,
}: ResizableSidebarProps) {
  const sidebarWidth = 170;
  const mobileAsideVisibilityClass = isMobileOpen
    ? 'translate-x-0 opacity-100 visible pointer-events-auto'
    : '-translate-x-full opacity-0 invisible pointer-events-none';

  return (
    <>
      {/* 移动端遮罩 */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm transition-all duration-300 lg:hidden animate-in fade-in"
          onClick={() => setIsMobileOpen?.(false)}
        />
      )}

      {/* 侧边栏 */}
      <aside
        style={{ width: `${sidebarWidth}px` }}
        className={`
          fixed left-0 top-0 z-50 h-screen transition-[transform,opacity,visibility] duration-300 lg:z-40
          bg-[color-mix(in_srgb,var(--od-bg-secondary)_88%,transparent)] backdrop-blur-xl
          will-change-transform lg:bg-transparent lg:backdrop-blur-none
          ${mobileAsideVisibilityClass}
          ${isCollapsed ? 'lg:-translate-x-full' : 'lg:translate-x-0'}
          lg:visible lg:pointer-events-auto lg:opacity-100
        `}
        aria-hidden={!isMobileOpen}
      >
        {/* 移动端关闭按钮 — 偏右上角，避开 logo 区域 */}
        <button
          onClick={() => setIsMobileOpen?.(false)}
          className="absolute right-2 top-3 z-10 rounded-lg p-1.5 text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)] lg:hidden"
          aria-label="关闭菜单"
        >
          <X className="h-4 w-4" />
        </button>

        {/* PC端收起按钮：与侧边栏右边缘融合，默认低调，悬停时凸显（仅在展开时显示） */}
        {!isCollapsed && (
          <button
            onClick={() => setIsCollapsed?.(true)}
            className="absolute right-0 top-1/2 z-10 hidden h-16 -translate-y-1/2 rounded-l-full px-1 text-[var(--od-text-tertiary)] opacity-20 transition-all duration-200 hover:opacity-100 hover:bg-white/[0.06] hover:text-[var(--od-text-primary)] lg:flex lg:items-center lg:justify-center"
            aria-label="收起侧边栏"
          >
            <ChevronLeft className="h-4 w-4 transition-transform duration-300" />
          </button>
        )}

        {/* 侧边栏内容 */}
        <div className="flex h-full flex-col overflow-y-auto">{children}</div>
      </aside>

      {/* PC端折叠状态下的展开按钮：固定在页面左侧中点，侧边栏完全隐藏时可点击 */}
      {isCollapsed && (
        <button
          onClick={() => setIsCollapsed?.(false)}
          className="fixed left-0 top-1/2 z-40 hidden h-16 -translate-y-1/2 rounded-r-full border border-white/[0.06] bg-[var(--od-bg-tertiary)] px-1 text-[var(--od-text-tertiary)] opacity-20 transition-all duration-200 hover:opacity-100 hover:bg-white/[0.1] hover:text-[var(--od-text-primary)] lg:flex lg:items-center lg:justify-center"
          aria-label="展开侧边栏"
        >
          <ChevronLeft className="h-4 w-4 rotate-180 transition-transform duration-300" />
        </button>
      )}
    </>
  );
}
