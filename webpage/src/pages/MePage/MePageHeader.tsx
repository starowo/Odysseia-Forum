import type { ComponentType } from 'react';
import { UserHeaderCard } from '@/entities/user/UserHeaderCard';
import { UserStatsGrid } from '@/entities/user/UserStatsGrid';
import type { User } from '@/features/auth/api/authApi';

export interface MePageTabOption {
  key: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

interface MePageHeaderProps {
  currentTab: string;
  onOpenProfile: () => void;
  onSelectTab: (tab: string) => void;
  showProfileButton: boolean;
  stats: Array<{ label: string; value: number; icon: ComponentType<{ className?: string }> }>;
  tabOptions: MePageTabOption[];
  user?: User;
}

export function MePageHeader({
  currentTab,
  onOpenProfile,
  onSelectTab,
  showProfileButton,
  stats,
  tabOptions,
  user,
}: MePageHeaderProps) {
  return (
    <section>
      <div className="flex flex-col gap-8">
        {showProfileButton && (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onOpenProfile}
              className="od-inline-action od-inline-action-ghost w-full justify-center sm:w-auto"
            >
              查看作者页
            </button>
          </div>
        )}

        <UserHeaderCard
          user={user}
          subtitle="这里是你的个人空间，书单、关注、创建的内容和偏好都在这里啦。"
        />

        <UserStatsGrid items={stats} />

        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex flex-wrap items-center justify-center gap-2">
            {tabOptions.map((item) => {
              const Icon = item.icon;
              const active = currentTab === item.key;
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => onSelectTab(item.key)}
                  className={`od-pill-chip inline-flex items-center gap-1.5 text-xs transition-colors ${
                    active
                      ? 'bg-[var(--od-accent)] text-white font-od-bold'
                      : 'text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)] font-od-medium'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </button>
              );
            })}
          </div>
          <p className="text-sm leading-6 text-[var(--od-text-secondary)]">
            在这里切换查看你的书单、关注、创建内容、足迹和搜索偏好，分类看更清晰。
          </p>
        </div>
      </div>
    </section>
  );
}
