import type { Channel } from '@/types/thread.types';

// 移植自 webpage_reference/config.js
// 当后端 /meta/channels 接口不可用时使用此配置
export const STATIC_CHANNEL_CATEGORIES = [
    {
        name: "分类1",
        channels: [
            { id: "122", name: "频道1" }
        ]
    },
    {
        name: "分类2",
        channels: [
            { id: "123", name: "频道2" }
        ]
    }
];

// 扁平化处理，适配 Channel[] 类型
export const FALLBACK_CHANNELS: Channel[] = STATIC_CHANNEL_CATEGORIES.flatMap(category =>
    category.channels.map(channel => ({
        id: channel.id,
        name: channel.name,
        // 静态配置中没有 tags 信息，设为空数组
        tags: []
    }))
);
