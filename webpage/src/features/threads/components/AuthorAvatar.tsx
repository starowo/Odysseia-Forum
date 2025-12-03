import { LazyImage } from '@/components/common/LazyImage';
import { getAvatarUrl } from '@/lib/utils/discord';

interface AuthorAvatarProps {
    author?: {
        id?: string;
        avatar?: string | null;
        avatar_url?: string;
        name?: string;
        global_name?: string;
    };
    size?: number;
    className?: string;
}

/**
 * 作者头像组件 - 统一处理Discord头像URL逻辑
 */
export function AuthorAvatar({ author, size = 128, className = 'h-8 w-8' }: AuthorAvatarProps) {
    const authorName = author?.global_name || author?.name || '未知用户';

    // 优先使用avatar_url,其次使用getAvatarUrl构建,最后使用默认头像
    const avatarUrl =
        author?.avatar_url ||
        (author?.id
            ? getAvatarUrl({
                id: author.id,
                avatar: author.avatar,
            }, size)
            : 'https://cdn.discordapp.com/embed/avatars/0.png');

    return (
        <div className={`relative flex-shrink-0 overflow-hidden rounded-full bg-[var(--od-bg-tertiary)] ${className}`}>
            <LazyImage src={avatarUrl} alt={authorName} className="h-full w-full object-cover" />
        </div>
    );
}
