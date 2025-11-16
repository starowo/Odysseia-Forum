import { Link, useLocation } from 'react-router-dom';
import { Search, Bookmark, TestTube, LogOut } from 'lucide-react';
import { toast } from 'sonner';

export function DevNav() {
  const location = useLocation();
  
  const handleLogout = () => {
    localStorage.clear();
    toast.success('已退出登录');
    window.location.href = '/login';
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="fixed bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full border border-[var(--od-border)] bg-[color-mix(in_oklab,var(--od-bg-secondary)_95%,transparent)] px-4 py-2 shadow-2xl backdrop-blur-lg transition-all duration-300">
      <div className="flex items-center gap-2">
        <Link
          to="/"
          className={`rounded-full p-2 transition-all duration-200 hover:scale-110 ${
            isActive('/') ? 'bg-[var(--od-accent)] text-white' : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
          }`}
          title="搜索页面"
        >
          <Search className="h-5 w-5" />
        </Link>
        
        <Link
          to="/follows"
          className={`rounded-full p-2 transition-all duration-200 hover:scale-110 ${
            isActive('/follows') ? 'bg-[var(--od-accent)] text-white' : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
          }`}
          title="关注列表"
        >
          <Bookmark className="h-5 w-5" />
        </Link>

        <Link
          to="/test"
          className={`rounded-full p-2 transition-all duration-200 hover:scale-110 ${
            isActive('/test') ? 'bg-[var(--od-accent)] text-white' : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
          }`}
          title="测试页面"
        >
          <TestTube className="h-5 w-5" />
        </Link>

        <div className="mx-2 h-6 w-px bg-[var(--od-border-strong)]" />

        <button
          onClick={handleLogout}
          className="rounded-full p-2 text-[var(--od-text-secondary)] transition-all duration-200 hover:scale-110 hover:bg-[color-mix(in_oklab,var(--od-error)_15%,transparent)] hover:text-[var(--od-error)]"
          title="退出登录"
        >
          <LogOut className="h-5 w-5" />
        </button>
      </div>
    </nav>
  );
}
