import { MascotEmotion } from '../assets';

export interface MascotMessage {
    emotion: MascotEmotion | MascotEmotion[];
    text: string | string[];
}

export const MASCOT_MESSAGES = {
    idle: [
        { emotion: 'hi', text: '有什么我可以帮你的吗？' },
        { emotion: 'tea', text: '要不要喝杯茶休息一下？' },
        { emotion: 'write', text: '正在记录你的每一次探索...' },
        { emotion: 'pride', text: '类脑Odysseia 是个好名字对吧？' },
        { emotion: 'sleep', text: '呼... 稍微有点困了呢...' },
    ] as MascotMessage[],

    search: {
        start: { emotion: 'searching', text: '正在努力检索中...' } as MascotMessage,
        empty: { emotion: 'confused', text: '唔... 好像找不到相关内容呢。' } as MascotMessage,
        found: { emotion: 'success', text: '找到啦！快来看看吧！' } as MascotMessage,
    },

    error: {
        generic: { emotion: 'sad_apology', text: '哎呀，好像出了点问题...' } as MascotMessage,
        network: { emotion: 'sad_apology', text: '网络连接好像不太顺畅...' } as MascotMessage,
    },

    // Special triggers for specific keywords
    keywords: [
        {
            keywords: ['shiyue137'],
            message: { emotion: 'pride', text: '这就是写网站的那个人哦。' }
        },
        {
            keywords: ['类脑娘'],
            message: { emotion: 'success', text: '那就是我！' }
        },
        {
            keywords: ['samb', '类脑rbq'],
            message: { emotion: 'samb', text: ['真淫乱!', '噢噢噢...哦哦哦齁❤️~'] }
        },
        {
            keywords: ['durvis', 'd喵'],
            message: { emotion: 'durvis', text: '旅程独立啦' }
        },
        {
            keywords: ['gemini', 'claude', 'gpt', 'openai', 'deepseek', 'llama', 'mistral'],
            message: { emotion: 'write', text: ['我也想变得像它们一样聪明...', '正在努力学习这些模型的知识...'] }
        },
        {
            keywords: ['棍母'],
            message: { emotion: 'confused', text: '这里什么都没有...' }
        },
    ] as { keywords: string[]; message: MascotMessage }[],
};
