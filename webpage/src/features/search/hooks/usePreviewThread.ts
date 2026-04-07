import { usePreviewStore } from '@/features/search/store/previewStore';
import type { Thread } from '@/entities/thread/types';

export function usePreviewThread() {
  const setPreviewThread = usePreviewStore((state) => state.setPreviewThread);
  const setPreviewThreadId = usePreviewStore((state) => state.setPreviewThreadId);

  const openPreview = (thread: Thread) => {
    setPreviewThread(thread);
  };

  const openPreviewById = (threadId: string) => {
    setPreviewThreadId(threadId);
  };

  return {
    openPreview,
    openPreviewById,
  };
}
