import { UserRound } from 'lucide-react';
import type { User } from '@/features/auth/api/authApi';

interface UserHeaderCardProps {
  user?: User;
  subtitle?: string;
}

export function UserHeaderCard({ user, subtitle }: UserHeaderCardProps) {
  const avatar = user?.avatar
    ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`
    : 'https://cdn.discordapp.com/embed/avatars/0.png';

  return (
    <div className="od-fluid-panel rounded-2xl p-5">
      <div className="flex items-center gap-3">
        <div className="relative h-12 w-12 overflow-hidden rounded-full bg-[var(--od-bg-tertiary)]">
          <img src={avatar} alt={user?.username || 'user'} className="h-full w-full object-cover" />
          <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-[var(--od-card)] bg-green-500" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate od-text-title">
            {user?.global_name || user?.username || '未登录'}
          </p>
          <p className="truncate od-text-meta mt-0.5">@{user?.username || '-'}</p>
        </div>
        <div className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--od-accent)]/12 text-[var(--od-accent)]">
          <UserRound className="h-4 w-4" />
        </div>
      </div>
      {subtitle && <p className="mt-3 od-text-body">{subtitle}</p>}
    </div>
  );
}
