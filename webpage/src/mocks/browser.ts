import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

// 配置一个包含了我们所有 Mock 规则的 Service Worker
export const worker = setupWorker(...handlers);