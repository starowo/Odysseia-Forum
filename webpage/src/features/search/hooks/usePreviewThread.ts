import { usePreviewStore } from '@/features/search/store/previewStore';
import type { Thread } from '@/entities/thread/types';
import { addBrowseHistory } from '@/shared/lib/browseHistory';

export function usePreviewThread() {
  const setPreviewThread = usePreviewStore((state) => state.setPreviewThread);
  const setPreviewThreadId = usePreviewStore((state) => state.setPreviewThreadId);

  const openPreview = (thread: Thread) => {
    addBrowseHistory(thread);
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
