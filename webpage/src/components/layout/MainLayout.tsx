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
    <div className="flex min-h-screen bg-[#282a2e]">
      {/* 侧边栏 */}
      <ResizableSidebar
        defaultWidth={240}
        minWidth={200}
        maxWidth={400}
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
      >
        <AppSidebar />
      </ResizableSidebar>

      {/* 主内容区 */}
      <main className="flex-1 bg-[#282a2e] pb-20 lg:ml-[240px]">
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
