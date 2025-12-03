import { ExternalLink } from 'lucide-react';
import { Tooltip } from '@/components/common/Tooltip';
import { DiscordIcon } from '@/components/icons/DiscordIcon';

interface ThreadActionsProps {
    threadId: string;
    guildId?: string;
    size?: 'sm' | 'md';
    className?: string;
}

/**
 * 帖子跳转按钮组件 - APP(Discord客户端) 和 WEB(浏览器)
 */
export function ThreadActions({ threadId, guildId, size = 'md', className }: ThreadActionsProps) {
    const finalGuildId = guildId || import.meta.env.VITE_GUILD_ID || '@me';
    const discordUrl = `https://discord.com/channels/${finalGuildId}/${threadId}`;
    const discordAppUrl = `discord://discord.com/channels/${finalGuildId}/${threadId}`;

    const sizeClasses = {
        sm: {
            container: 'gap-2',
            button: 'gap-1 px-2.5 py-1 text-xs',
            icon: 'h-3.5 w-3.5',
        },
        md: {
            container: 'gap-2',
            button: 'gap-1.5 px-3 py-1.5 text-sm',
            icon: 'h-4 w-4',
        },
    };

    const classes = sizeClasses[size];

    return (
        <div className={`flex items-center ${classes.container} ${className || ''}`}>
            {/* APP按钮 - Discord客户端 */}
            <Tooltip content="在 Discord App 中打开" position="left">
                <a
                    href={discordAppUrl}
                    onClick={(e) => e.stopPropagation()}
                    className={`flex items-center rounded-lg bg-[var(--od-accent)] ${classes.button} font-medium text-white opacity-0 translate-y-1 transition-all duration-200 group-hover:opacity-100 group-hover:translate-y-0 hover:scale-105 hover:bg-[var(--od-accent-hover)]`}
                    aria-label="在Discord App中打开"
                >
                    <DiscordIcon className={classes.icon} />
                    <span>APP</span>
                </a>
            </Tooltip>

            {/* WEB按钮 - 浏览器 */}
            <Tooltip content="在浏览器中打开" position="left">
                <a
                    href={discordUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className={`flex items-center rounded-lg bg-[var(--od-accent-secondary)] hover:bg-[var(--od-accent-secondary-hover)] ${classes.button} font-medium text-white opacity-0 translate-y-1 transition-all duration-200 group-hover:opacity-100 group-hover:translate-y-0 hover:scale-105 border border-[var(--od-border)]`}
                    aria-label="在浏览器中打开"
                >
                    <ExternalLink className={classes.icon} />
                    <span>WEB</span>
                </a>
            </Tooltip>
        </div>
    );
}
