import type { MascotEmotion } from '@/features/mascot/assets';
import { MASCOT_MESSAGES, type MascotMessage } from '@/features/mascot/config/triggers';

export type MascotErrorType = 'generic' | 'network' | 'notFound';
export type MascotSearchStatus = 'start' | 'empty' | 'found';

export interface ResolvedMascotMessage {
  emotion: MascotEmotion;
  message: string;
}

export function resolveIdleMascotMessage(): ResolvedMascotMessage {
  const selected = pickRandom(MASCOT_MESSAGES.idle);
  return resolveMascotMessage(selected);
}

export function resolveErrorMascotMessage(type: MascotErrorType = 'generic'): ResolvedMascotMessage {
  return resolveMascotMessage(MASCOT_MESSAGES.error[type]);
}

export function resolveSearchMascotMessage(
  status: MascotSearchStatus,
  query?: string,
): ResolvedMascotMessage {
  let selected = MASCOT_MESSAGES.search[status];

  if (query) {
    const lowerQuery = query.toLowerCase();

    for (const trigger of MASCOT_MESSAGES.keywords) {
      if (trigger.keywords.some((keyword) => lowerQuery.includes(keyword.toLowerCase()))) {
        selected = trigger.message;
        break;
      }
    }
  }

  return resolveMascotMessage(selected);
}

function resolveMascotMessage(source: MascotMessage): ResolvedMascotMessage {
  return {
    emotion: pickRandom(source.emotion),
    message: pickRandom(source.text),
  };
}

function pickRandom<T>(value: T | T[]): T {
  if (Array.isArray(value)) {
    return value[Math.floor(Math.random() * value.length)];
  }

  return value;
}
