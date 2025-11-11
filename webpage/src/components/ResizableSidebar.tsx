import { useState, useRef, useEffect, ReactNode } from 'react';
import { X } from 'lucide-react';

interface ResizableSidebarProps {
  children: ReactNode;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  isMobileOpen?: boolean;
  setIsMobileOpen?: (open: boolean) => void;
}

export function ResizableSidebar({
  children,
  defaultWidth = 240,
  minWidth = 200,
  maxWidth = 400,
  isMobileOpen = false,
  setIsMobileOpen,
}: ResizableSidebarProps) {
  const [width, setWidth] = useState(defaultWidth);
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;

      const newWidth = e.clientX;
      if (newWidth >= minWidth && newWidth <= maxWidth) {
        setWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, minWidth, maxWidth]);

  return (
    <>
      {/* 移动端遮罩 */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setIsMobileOpen?.(false)}
        />
      )}

      {/* 侧边栏 */}
      <aside
        ref={sidebarRef}
        style={{ width: `${width}px` }}
        className={`
          fixed left-0 top-0 z-50 h-screen border-r border-[#1e1f22] bg-[#2b2d31] transition-transform
          lg:translate-x-0
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* 移动端关闭按钮 */}
        <button
          onClick={() => setIsMobileOpen?.(false)}
          className="absolute right-4 top-4 rounded-lg p-2 text-[#949ba4] hover:bg-[#35373c] hover:text-[#f2f3f5] lg:hidden"
          aria-label="关闭菜单"
        >
          <X className="h-5 w-5" />
        </button>

        {/* 侧边栏内容 */}
        <div className="flex h-full flex-col overflow-y-auto p-4">{children}</div>

        {/* PC端拖拽手柄 */}
        <div
          onMouseDown={() => setIsResizing(true)}
          className="absolute right-0 top-0 hidden h-full w-1 cursor-col-resize hover:bg-[#5865f2]/50 lg:block"
          aria-label="调整侧边栏宽度"
        >
          <div className="absolute right-0 top-1/2 h-12 w-1 -translate-y-1/2 rounded-full bg-[#4e5058]" />
        </div>
      </aside>
    </>
  );
}
