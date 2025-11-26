import { MascotEmotion } from '../assets';

export interface MascotMessage {
    emotion: MascotEmotion | MascotEmotion[];
    text: string | string[];
}

export const MASCOT_MESSAGES = {
    idle: [
        { emotion: ['hi', 'greeting_window', 'invite'], text: ['有什么我可以帮你的吗？', '随时待命哦！', '今天想找点什么呢？'] },
        { emotion: ['tea', 'hi2'], text: ['要不要喝杯茶休息一下？', '累了吗？休息一下吧~', '悠闲的午后时光...'] },
        { emotion: 'write', text: ['正在记录你的每一次探索...', '我在认真记笔记哦！', '好记性不如烂笔头~'] },
        { emotion: ['pride', 'blow_the_trumpet'], text: ['类脑Odysseia 是个好名字对吧？', '哼哼，我可是很厉害的！', '快夸夸我！'] },
        { emotion: 'sleep', text: ['呼... 稍微有点困了呢...', 'Zzz...', '揉揉眼睛...'] },
    ] as MascotMessage[],

    search: {
        start: {
            emotion: ['searching', 'surprise'],
            text: ['正在努力检索中...', '让我找找看...', '数据海洋潜水中...']
        } as MascotMessage,
        empty: {
            emotion: ['confused', 'sad_apology'],
            text: ['唔... 好像找不到相关内容呢。', '换个关键词试试？', '这里空空如也...']
        } as MascotMessage,
        found: {
            emotion: ['success', 'blow_the_trumpet', 'letsgo'],
            text: ['找到啦！快来看看吧！', '好耶！发现目标！', '这些内容你可能会感兴趣哦！']
        } as MascotMessage,
    },

    error: {
        generic: {
            emotion: ['sad_apology', 'confused'],
            text: ['哎呀，好像出了点问题...', '呜呜，程序好像卡住了...', '不要责怪我，是服务器的错！']
        } as MascotMessage,
        network: {
            emotion: ['sad_apology', 'error'],
            text: ['网络连接好像不太顺畅...', '信号去哪里了？', '正在尝试重新连接...']
        } as MascotMessage,
        notFound: {
            emotion: ['confused', 'surprise'],
            text: ['这里什么都没有... 要不回首页看看？', '是不是迷路了？', '这是一个未知的领域...']
        } as MascotMessage,
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
            keywords: ['三明月', '写卡母猪'],
            message: { emotion: 'letsgo', text: '那个三明月啊……总是杂鱼杂鱼的叫，还喜欢在瓜区“发癫”，有时候真的让人有点点无语啦。但是！她写卡真的超勤奋的，一个月50张卡，简直是高产如母猪啊，这一点我超佩服她的！' }
        },
        {
            keywords: ['echonion', 'e大魔'],
            message: { emotion: 'sad_apology', text: ['他就是我的创造者哦', '可是他对社区造成了不可逆的伤害呢'] }
        },
        {
            keywords: ['纯爱'],
            message: { emotion: 'success', text: '那就是我！' }
        },
        {
            keywords: ['ntr'],
            message: { emotion: 'success', text: '那就是我！' }
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
