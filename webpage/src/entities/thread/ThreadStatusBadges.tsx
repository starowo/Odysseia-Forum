import { Bell, Sparkles } from 'lucide-react';

interface ThreadStatusBadgesProps {
    isFollowing?: boolean;
    hasUpdate?: boolean;
    variant?: 'card' | 'list' | 'detail';
    className?: string;
}

export function ThreadStatusBadges({
    isFollowing,
    hasUpdate,
    variant = 'card',
    className = ''
}: ThreadStatusBadgesProps) {
    if (!isFollowing && !hasUpdate) return null;

    // Card variant: Absolute positioning (top-left)
    if (variant === 'card') {
        return (
            <div className={`absolute left-2 top-2 z-20 flex flex-col gap-1.5 ${className}`}>
                {hasUpdate && (
                    <div className="flex items-center gap-1 rounded-full bg-[#23a55a]/90 px-2 py-0.5 text-xs font-semibold text-white shadow-sm backdrop-blur-sm animate-in fade-in slide-in-from-top-2 duration-300">
                        <span className="inline-block h-2 w-2 rounded-full bg-white animate-[pulse_2.4s_ease-in-out_infinite]" />
                        <span>有更新</span>
                    </div>
                )}
                {isFollowing && (
                    <div className="flex items-center gap-1 rounded-full bg-[var(--od-accent)]/90 px-2 py-0.5 text-xs font-semibold text-white shadow-sm backdrop-blur-sm animate-in fade-in slide-in-from-top-2 duration-300 delay-75">
                        <Bell className="h-3 w-3 fill-current" />
                        <span>已关注</span>
                    </div>
                )}
            </div>
        );
    }

    // List & Detail variant: Inline positioning
    const sizeClasses = variant === 'detail' ? 'h-5 px-2 text-xs' : 'h-4 px-1.5 text-[10px]';
    const iconSizes = variant === 'detail' ? 'h-3.5 w-3.5' : 'h-3 w-3';

    return (
        <div className={`inline-flex items-center gap-2 align-middle ${className}`}>
            {hasUpdate && (
                <span
                    className={`inline-flex items-center gap-1 rounded-full bg-[#23a55a]/10 font-medium text-[#23a55a] border border-[#23a55a]/20 ${sizeClasses}`}
                    title="该帖子有新的更新"
                >
                    <Sparkles className={iconSizes} />
                    <span>有更新</span>
                </span>
            )}
            {isFollowing && (
                <span
                    className={`inline-flex items-center gap-1 rounded-full bg-[var(--od-accent)]/10 font-medium text-[var(--od-accent)] border border-[var(--od-accent)]/20 ${sizeClasses}`}
                    title="你已关注此帖子"
                >
                    <Bell className={`${iconSizes} fill-current`} />
                    <span>已关注</span>
                </span>
            )}
        </div>
    );
}
