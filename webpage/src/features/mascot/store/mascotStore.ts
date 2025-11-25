import { create } from 'zustand';
import { MascotEmotion } from '../assets';
import { MASCOT_MESSAGES } from '../config/triggers';

interface MascotState {
    emotion: MascotEmotion;
    message: string;
    isVisible: boolean;
    isAnimating: boolean;

    // Actions
    say: (message: string, emotion?: MascotEmotion, duration?: number) => void;
    setEmotion: (emotion: MascotEmotion) => void;
    setVisible: (visible: boolean) => void;
    reset: () => void;
    reactToSearch: (status: 'start' | 'empty' | 'found', query?: string) => void;
    reactToError: (type?: 'generic' | 'network') => void;
}

const DEFAULT_STATE = {
    emotion: 'hi' as MascotEmotion,
    message: '今天也是充满希望的一天呢！',
    isVisible: true,
    isAnimating: false,
};

export const useMascotStore = create<MascotState>((set, get) => ({
    ...DEFAULT_STATE,

    say: (message, emotion) => {
        set({
            message,
            emotion: emotion || get().emotion,
            isVisible: true,
            isAnimating: true
        });
        setTimeout(() => set({ isAnimating: false }), 300);
    },

    setEmotion: (emotion) => set({ emotion }),

    setVisible: (visible) => set({ isVisible: visible }),

    reset: () => {
        const idleMessages = MASCOT_MESSAGES.idle;
        const randomMsg = idleMessages[Math.floor(Math.random() * idleMessages.length)];

        set({
            emotion: pickRandom(randomMsg.emotion),
            message: pickRandom(randomMsg.text),
            isAnimating: true
        });
        setTimeout(() => set({ isAnimating: false }), 300);
    },

    reactToSearch: (status, query) => {
        let msg = MASCOT_MESSAGES.search[status];

        // 1. Check for keyword triggers first
        if (query) {
            const lowerQuery = query.toLowerCase();
            const keywordTriggers = MASCOT_MESSAGES.keywords;

            for (const trigger of keywordTriggers) {
                if (trigger.keywords.some(k => lowerQuery.includes(k.toLowerCase()))) {
                    msg = trigger.message;
                    break;
                }
            }
        }

        get().say(pickRandom(msg.text), pickRandom(msg.emotion));
    },

    reactToError: (type = 'generic') => {
        const msg = MASCOT_MESSAGES.error[type];
        get().say(pickRandom(msg.text), pickRandom(msg.emotion));
    },
}));

// Helper to pick a random value from a string or string array
function pickRandom(value: string | string[]): string {
    if (Array.isArray(value)) {
        return value[Math.floor(Math.random() * value.length)];
    }
    return value;
}
