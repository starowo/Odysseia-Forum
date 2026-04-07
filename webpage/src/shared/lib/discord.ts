export const DISCORD_CDN_BASE = 'https://cdn.discordapp.com';

export interface DiscordUser {
    id: string;
    avatar?: string | null;
    discriminator?: string;
}

/**
 * 获取 Discord 用户头像 URL
 * @param user 用户对象 (包含 id 和 avatar)
 * @param size 头像大小 (默认 128)
 * @returns 头像 URL
 */
export function getAvatarUrl(user: DiscordUser, size: number = 128): string {
    if (user.avatar) {
        const format = user.avatar.startsWith('a_') ? 'gif' : 'png';
        return `${DISCORD_CDN_BASE}/avatars/${user.id}/${user.avatar}.${format}?size=${size}`;
    }

    // 默认头像逻辑
    // Discord 默认头像计算方式: (user_id >> 22) % 6
    let index = 0;
    try {
        index = Number((BigInt(user.id) >> 22n) % 6n);
    } catch (e) {
        // 如果 ID 不是纯数字（例如 mock 数据），使用简单的 hash
        index = user.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % 6;
    }
    return `${DISCORD_CDN_BASE}/embed/avatars/${index}.png`;
}
