import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { usePreviewStore } from '@/features/search/store/previewStore';
import { ThreadPreviewOverlay } from '@/widgets/thread-preview/ThreadPreviewOverlay';
import { searchApi } from '@/features/search/api/searchApi';
import { searchKeys } from '@/features/search/lib/queryKeys';
import { showMascotToast } from '@/features/mascot/lib/mascotToast';
import { addBrowseHistory } from '@/shared/lib/browseHistory';

export function GlobalThreadPreview() {
    const previewThread = usePreviewStore((state) => state.previewThread);
    const previewThreadId = usePreviewStore((state) => state.previewThreadId);
    const previewOptions = usePreviewStore((state) => state.previewOptions);
    const setPreviewThread = usePreviewStore((state) => state.setPreviewThread);

    // Fetch thread details if only ID is provided
    const { data: fetchedThread, isError } = useQuery({
        queryKey: searchKeys.thread(previewThreadId),
        queryFn: () => searchApi.getThread(previewThreadId!),
        enabled: !!previewThreadId,
        staleTime: 5 * 60 * 1000,
    });

    // Handle fetch error
    useEffect(() => {
        if (isError) {
            showMascotToast({
                id: 'thread-preview-load-error',
                emotion: 'confused',
                eyebrow: 'Preview Interrupted',
                title: '帖子详情没拉下来',
                message: '这条帖子的预览没能顺利展开，等会儿再试试看。',
            });
            setPreviewThread(null); // Close overlay
        }
    }, [isError, setPreviewThread]);

    // Determine which thread to show (fetched or directly provided)
    const threadToShow = previewThread || (previewThreadId && fetchedThread ? fetchedThread : null);

    useEffect(() => {
        if (!threadToShow) return;
        addBrowseHistory(threadToShow);
    }, [threadToShow]);

    if (!threadToShow) return null;

    return (
        <ThreadPreviewOverlay
            thread={threadToShow}
            onClose={() => setPreviewThread(null)}
            externalUrlOverride={previewOptions?.externalUrlOverride}
            hideExternalButton={previewOptions?.hideExternalButton}
        />
    );
}
