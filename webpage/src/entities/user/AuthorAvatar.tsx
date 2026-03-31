import { LazyImage } from '@/shared/ui/LazyImage';
import type { Author } from '@/entities/thread/types';

interface AuthorAvatarProps {
    author?: Author | null;
    className?: string;
}

/**
 * 作者头像组件 - 统一处理Discord头像URL逻辑
 */
export function AuthorAvatar({ author, className = 'h-8 w-8' }: AuthorAvatarProps) {
    const authorName = author?.global_name || author?.name || '未知用户';

    // 优先使用 avatar_url, 其次使用 fallback 用户默认头像
    const avatarUrl =
        author?.avatar_url ||
        'https://cdn.discordapp.com/embed/avatars/0.png';

    return (
        <div className={`relative flex-shrink-0 overflow-hidden rounded-full bg-[var(--od-bg-tertiary)] ${className}`}>
            <LazyImage src={avatarUrl} alt={authorName} className="h-full w-full object-cover" />
        </div>
    );
}
