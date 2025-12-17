import { Tooltip } from '@/components/common/Tooltip';
import { DiscordIcon } from '@/components/icons/DiscordIcon';
import { useSettings } from '@/hooks/useSettings';
import { AnimatedIcon } from '@/components/ui/animation/AnimatedIcon';
import { useState } from 'react';

interface ThreadActionsProps {
    threadId: string;
    guildId?: string;
    size?: 'sm' | 'md';
    variant?: 'default' | 'white' | 'glass';
    alwaysVisible?: boolean;
    className?: string;
    externalUrlOverride?: string | null;
}

/**
 * 帖子跳转按钮组件 - 根据全局设置决定跳转 APP 还是 WEB
 * variant: 
 *  - 'default': 主题色，用于普通背景
 *  - 'white': 白色，用于深色背景/图片上
 *  - 'glass': 毛玻璃圆形按钮，用于卡片封面悬浮（与刷新按钮一致）
 */
export function ThreadActions({ threadId, guildId, size = 'md', variant = 'default', alwaysVisible = false, className, externalUrlOverride }: ThreadActionsProps) {
    const { settings } = useSettings();
    const [isHovered, setIsHovered] = useState(false);
    const finalGuildId = guildId || import.meta.env.VITE_GUILD_ID || '@me';

    // 根据设置决定目标 URL
    const targetUrl = settings.openMode === 'web'
        ? (externalUrlOverride || `https://discord.com/channels/${finalGuildId}/${threadId}`)
        : (externalUrlOverride || `discord://discord.com/channels/${finalGuildId}/${threadId}`);

    const isWeb = settings.openMode === 'web';
    const tooltipContent = isWeb ? "在浏览器中打开" : "在 Discord App 中打开";

    // 样式配置
    const sizeClasses = {
        sm: {
            button: 'p-1.5',
            icon: 'h-3.5 w-3.5',
        },
        md: {
            button: 'p-2',
            icon: 'h-4 w-4',
        },
    };

    // Glass 变体强制使用特定尺寸和样式（覆盖 size 属性）
    if (variant === 'glass') {
        return (
            <Tooltip content={tooltipContent} position="left">
                <a
                    href={targetUrl}
                    target={isWeb ? "_blank" : undefined}
                    rel={isWeb ? "noopener noreferrer" : undefined}
                    onClick={(e) => e.stopPropagation()}
                    onMouseEnter={() => setIsHovered(true)}
                    onMouseLeave={() => setIsHovered(false)}
                    className={`flex h-8 w-8 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur-md transition-colors hover:bg-black/60 ${className || ''}`}
                    aria-label={tooltipContent}
                >
                    <AnimatedIcon icon={DiscordIcon} className="h-4 w-4" animation="shake" isHovered={isHovered} />
                </a>
            </Tooltip>
        );
    }

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
        <div className={`flex items-center ${className || ''}`}>
            <Tooltip content={tooltipContent} position="left">
                <a
                    href={targetUrl}
                    target={isWeb ? "_blank" : undefined}
                    rel={isWeb ? "noopener noreferrer" : undefined}
                    onClick={(e) => e.stopPropagation()}
                    onMouseEnter={() => setIsHovered(true)}
                    onMouseLeave={() => setIsHovered(false)}
                    className={`flex items-center justify-center rounded-md transition-all duration-200 ${classes.button} ${colorClasses} ${visibilityClasses}`}
                    aria-label={tooltipContent}
                >
                    <AnimatedIcon icon={DiscordIcon} className={classes.icon} animation="shake" isHovered={isHovered} />
                </a>
            </Tooltip>
        </div>
    );
}
