import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { usePreviewStore } from '@/features/search/store/previewStore';
import { ThreadPreviewOverlay } from '@/widgets/thread-preview/ThreadPreviewOverlay';
import { searchApi } from '@/features/search/api/searchApi';
import { searchKeys } from '@/features/search/lib/queryKeys';
import { toast } from 'sonner';

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
            toast.error('无法加载帖子详情');
            setPreviewThread(null); // Close overlay
        }
    }, [isError, setPreviewThread]);

    // Determine which thread to show (fetched or directly provided)
    const threadToShow = previewThread || (previewThreadId && fetchedThread ? fetchedThread : null);

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
