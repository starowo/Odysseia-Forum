import { Link, useLocation } from 'react-router-dom';
import { Search, Bookmark, TestTube, LogOut } from 'lucide-react';
import { isDevelopmentMode } from '@/lib/mockAuth';
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
    <nav className="fixed bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full border border-[#1e1f22] bg-[#2b2d31]/95 px-4 py-2 shadow-2xl backdrop-blur-lg transition-all duration-300">
      <div className="flex items-center gap-2">
        <Link
          to="/"
          className={`rounded-full p-2 transition-all duration-200 hover:scale-110 ${
            isActive('/') ? 'bg-[#5865f2] text-white' : 'text-[#b5bac1] hover:bg-[#4e5058] hover:text-[#f2f3f5]'
          }`}
          title="搜索页面"
        >
          <Search className="h-5 w-5" />
        </Link>
        
        <Link
          to="/follows"
          className={`rounded-full p-2 transition-all duration-200 hover:scale-110 ${
            isActive('/follows') ? 'bg-[#5865f2] text-white' : 'text-[#b5bac1] hover:bg-[#4e5058] hover:text-[#f2f3f5]'
          }`}
          title="关注列表"
        >
          <Bookmark className="h-5 w-5" />
        </Link>

        {isDevelopmentMode() && (
          <Link
            to="/test"
            className={`rounded-full p-2 transition-all duration-200 hover:scale-110 ${
              isActive('/test') ? 'bg-[#5865f2] text-white' : 'text-[#b5bac1] hover:bg-[#4e5058] hover:text-[#f2f3f5]'
            }`}
            title="测试页面"
          >
            <TestTube className="h-5 w-5" />
          </Link>
        )}

        <div className="mx-2 h-6 w-px bg-[#4e5058]" />

        <button
          onClick={handleLogout}
          className="rounded-full p-2 text-[#b5bac1] transition-all duration-200 hover:scale-110 hover:bg-[#f23f42]/20 hover:text-[#f23f42]"
          title="退出登录"
        >
          <LogOut className="h-5 w-5" />
        </button>
      </div>
    </nav>
  );
}
