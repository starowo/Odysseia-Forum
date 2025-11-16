import { useState, ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ResizableSidebar } from '@/components/ResizableSidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AppSidebar } from '@/components/layout/AppSidebar';

interface MainLayoutProps {
  children: ReactNode;
  showTopBar?: boolean;
  enableAutoSearch?: boolean;  // 允许页面自定义是否启用自动搜索
}

export function MainLayout({ children, showTopBar = true, enableAutoSearch }: MainLayoutProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const navigate = useNavigate();
  const location = useLocation();

  // 默认只在搜索页面（根路径）启用自动搜索
  const shouldEnableAutoSearch = enableAutoSearch ?? (location.pathname === '/');

  const handleSearch = () => {
    // 使用 React Router 导航，不会刷新页面
    if (searchInput.trim()) {
      navigate(`/?q=${encodeURIComponent(searchInput)}`);
    } else {
      navigate('/');
    }
  };

  return (
    <div className="flex min-h-screen bg-[var(--od-bg)]">
      {/* 侧边栏 */}
      <ResizableSidebar
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
      >
        <AppSidebar />
      </ResizableSidebar>

      {/* 主内容区：根据侧边栏折叠状态调整左侧留白（PC 端） */}
      <main
        className={`flex-1 bg-[var(--od-bg)] pb-20 transition-all duration-300 ${
          isSidebarCollapsed ? 'lg:ml-0' : 'lg:ml-[240px]'
        }`}
      >
        {showTopBar && (
          <TopBar
            searchValue={searchInput}
            onSearchChange={setSearchInput}
            onSearch={handleSearch}
            onMenuClick={() => setIsMobileOpen(true)}
            enableAutoSearch={shouldEnableAutoSearch}
          />
        )}
        {children}
      </main>
    </div>
  );
}
