import { ExternalLink } from 'lucide-react';
import { Tooltip } from '@/components/common/Tooltip';
import { DiscordIcon } from '@/components/icons/DiscordIcon';

interface ThreadActionsProps {
    threadId: string;
    guildId?: string;
    size?: 'sm' | 'md';
    variant?: 'default' | 'white';
    alwaysVisible?: boolean;
    className?: string;
}

/**
 * 帖子跳转按钮组件 - APP(Discord客户端) 和 WEB(浏览器)
 * variant: 'default' (主题色，用于普通背景) | 'white' (白色，用于深色背景/图片上)
 * alwaysVisible: 是否在桌面端始终显示（不依赖 group-hover）
 */
export function ThreadActions({ threadId, guildId, size = 'md', variant = 'default', alwaysVisible = false, className }: ThreadActionsProps) {
    const finalGuildId = guildId || import.meta.env.VITE_GUILD_ID || '@me';
    const discordUrl = `https://discord.com/channels/${finalGuildId}/${threadId}`;
    const discordAppUrl = `discord://discord.com/channels/${finalGuildId}/${threadId}`;

    const sizeClasses = {
        sm: {
            container: 'gap-1',
            button: 'p-1.5',
            icon: 'h-3.5 w-3.5',
        },
        md: {
            container: 'gap-1.5',
            button: 'p-2',
            icon: 'h-4 w-4',
        },
    };

    const classes = sizeClasses[size];

    // 颜色样式
    const colorClasses = variant === 'white'
        ? 'text-white/80 hover:text-white hover:bg-white/10'
        : 'text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)] hover:bg-[var(--od-bg-tertiary)]';

    // 可见性样式
    const visibilityClasses = alwaysVisible
        ? 'opacity-100 translate-y-0'
        : 'md:opacity-0 md:translate-y-1 md:group-hover:opacity-100 md:group-hover:translate-y-0';

    return (
        <div className={`flex items-center ${classes.container} ${className || ''}`}>
            {/* APP按钮 - Discord客户端 */}
            <Tooltip content="在 Discord App 中打开" position="left">
                <a
                    href={discordAppUrl}
                    onClick={(e) => e.stopPropagation()}
                    className={`flex items-center justify-center rounded-md transition-all duration-200 ${classes.button} ${colorClasses} ${visibilityClasses}`}
                    aria-label="在Discord App中打开"
                >
                    <DiscordIcon className={classes.icon} />
                </a>
            </Tooltip>

            {/* WEB按钮 - 浏览器 */}
            <Tooltip content="在浏览器中打开" position="left">
                <a
                    href={discordUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className={`flex items-center justify-center rounded-md transition-all duration-200 ${classes.button} ${colorClasses} ${visibilityClasses}`}
                    aria-label="在浏览器中打开"
                >
                    <ExternalLink className={classes.icon} />
                </a>
            </Tooltip>
        </div>
    );
}
