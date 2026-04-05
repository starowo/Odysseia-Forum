import { UserRound } from 'lucide-react';
import type { User } from '@/features/auth/api/authApi';

interface UserHeaderCardProps {
  user?: User;
  subtitle?: string;
  avatarUrl?: string | null;
}

export function UserHeaderCard({ user, subtitle, avatarUrl }: UserHeaderCardProps) {
  const avatar = avatarUrl || (user?.avatar
    ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`
    : 'https://cdn.discordapp.com/embed/avatars/0.png');

  return (
    <div className="px-1">
      <div className="flex flex-col items-center text-center">
        <div className="relative h-16 w-16 overflow-hidden rounded-full bg-[var(--od-bg-tertiary)] sm:h-20 sm:w-20">
          <img src={avatar} alt={user?.username || 'user'} className="h-full w-full object-cover" />
          <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-[var(--od-card)] bg-green-500" />
        </div>
        <div className="mt-4 min-w-0">
          <p className="truncate text-xs font-semibold uppercase tracking-[0.22em] text-[var(--od-text-tertiary)]">
            Personal Hub
          </p>
          <p className="mt-2 truncate text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-primary)]">
            {user?.global_name || user?.username || '未登录'}
          </p>
          <p className="mt-1 truncate text-sm text-[var(--od-text-secondary)]">@{user?.username || '-'}</p>
          {subtitle && <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)]">{subtitle}</p>}
        </div>
        <div className="mt-4 inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
          <UserRound className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}
