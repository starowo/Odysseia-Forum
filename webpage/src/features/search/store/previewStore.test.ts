import { describe, it, expect, beforeEach } from 'vitest';
import { usePreviewStore } from './previewStore';
import type { Thread } from '@/entities/thread/types';

describe('previewStore', () => {
  // 每次测试前重置 store 状态
  beforeEach(() => {
    usePreviewStore.setState({
      previewThread: null,
      previewThreadId: null,
      previewOptions: {},
    });
  });

  it('初始状态应该是干净的', () => {
    const state = usePreviewStore.getState();
    expect(state.previewThread).toBeNull();
    expect(state.previewThreadId).toBeNull();
  });

  it('setPreviewThread 应该正确设置 thread 并重置 id', () => {
    const mockThread = { thread_id: '1', title: 'Test' } as Thread;
    usePreviewStore.getState().setPreviewThread(mockThread, { hideExternalButton: true });

    const state = usePreviewStore.getState();
    expect(state.previewThread).toEqual(mockThread);
    expect(state.previewThreadId).toBeNull();
    expect(state.previewOptions.hideExternalButton).toBe(true);
  });

  it('setPreviewThreadId 应该正确设置 id 并重置 thread', () => {
    usePreviewStore.getState().setPreviewThreadId('999');

    const state = usePreviewStore.getState();
    expect(state.previewThreadId).toBe('999');
    expect(state.previewThread).toBeNull();
  });

  it('关闭预览应该清除所有数据', () => {
    usePreviewStore.getState().setPreviewThreadId('123');
    usePreviewStore.getState().setPreviewThreadId(null);

    const state = usePreviewStore.getState();
    expect(state.previewThreadId).toBeNull();
    expect(state.previewThread).toBeNull();
  });
});
