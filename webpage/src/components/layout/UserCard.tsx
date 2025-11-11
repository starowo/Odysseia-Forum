import { User } from 'lucide-react';

interface UserCardProps {
  avatar?: string;
  username: string;
  status?: 'online' | 'idle' | 'offline';
}

export function UserCard({ avatar, username, status = 'online' }: UserCardProps) {
  const statusColors = {
    online: 'bg-[#23a55a]',
    idle: 'bg-[#f0b232]',
    offline: 'bg-[#80848e]',
  };

  const statusLabels = {
    online: '在线',
    idle: '离开',
    offline: '离线',
  };

  return (
    <div className="mb-4 flex items-center gap-3 rounded-xl bg-[#232428] p-3 transition-all duration-200 hover:bg-[#2a2c31]">
      {/* 头像 */}
      <div className="relative">
        {avatar ? (
          <img
            src={avatar}
            alt={username}
            className="h-10 w-10 rounded-full"
          />
        ) : (
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#5865f2]">
            <User className="h-5 w-5 text-white" />
          </div>
        )}
        {/* 状态指示器 */}
        <div className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[#232428] ${statusColors[status]}`} />
      </div>

      {/* 用户信息 */}
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold text-[#f2f3f5]">
          {username}
        </div>
        <div className="text-xs text-[#949ba4]">
          {statusLabels[status]}
        </div>
      </div>
    </div>
  );
}
