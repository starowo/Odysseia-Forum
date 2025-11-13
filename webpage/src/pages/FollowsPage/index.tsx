import { useQuery } from '@tanstack/react-query';
import { Bookmark } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { ThreadCard } from '@/features/threads/components/ThreadCard';
import { ThreadCardSkeleton } from '@/features/threads/components/ThreadCardSkeleton';
import { followsApi } from '@/features/follows/api/followsApi';

export function FollowsPage() {
  // 使用真实API获取关注列表
  const { data: followsData, isLoading } = useQuery({
    queryKey: ['follows'],
    queryFn: followsApi.getFollows,
    staleTime: 60 * 1000, // 1分钟
  });

  const follows = followsData?.results || [];
  const unreadCount = followsData?.unread_count || 0;

  return (
    <MainLayout>
      <div>
        {/* 标题栏 */}
        <div className="border-b border-[#1e1f22] bg-[#2b2d31] px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bookmark className="h-6 w-6 text-[#f2f3f5]" />
              <div>
                <h1 className="text-xl font-bold text-[#f2f3f5]">我的关注</h1>
                <p className="text-sm text-[#b5bac1]">
                  共 {follows.length} 个帖子
                  {unreadCount > 0 && (
                    <span className="ml-2 rounded bg-[#23a55a] px-2 py-0.5 text-xs font-bold text-white">
                      {unreadCount} 个更新
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* 关注列表 */}
        <div className="p-4">
          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <ThreadCardSkeleton key={i} />
              ))}
            </div>
          ) : follows.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-in fade-in duration-500">
              {follows.map((thread, index) => (
                <div
                  key={thread.id}
                  className="animate-in fade-in slide-in-from-bottom-4"
                  style={{
                    animationDelay: `${index * 50}ms`,
                    animationFillMode: 'backwards',
                  }}
                >
                  <ThreadCard thread={thread} />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex min-h-[400px] items-center justify-center">
              <div className="text-center">
                <Bookmark className="mx-auto mb-4 h-16 w-16 text-[#4e5058]" />
                <h3 className="mb-2 text-xl font-bold text-[#f2f3f5]">
                  还没有关注任何帖子
                </h3>
                <p className="text-[#b5bac1]">
                  在Discord中使用Bot命令关注帖子
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
