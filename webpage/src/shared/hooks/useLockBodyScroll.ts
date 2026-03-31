import { useLayoutEffect } from 'react';

export function useLockBodyScroll(isLocked: boolean = true) {
    // Use useLayoutEffect to prevent initial flicker
    useLayoutEffect(() => {
        if (!isLocked) return;

        // Get original body style
        const originalStyle = window.getComputedStyle(document.body).overflow;
        const originalPaddingRight = document.body.style.paddingRight;

        // Calculate scrollbar width
        const scrollBarWidth = window.innerWidth - document.documentElement.clientWidth;

        // Apply styles
        document.body.style.overflow = 'hidden';

        // Only add padding if there is a scrollbar preventing content shift
        if (scrollBarWidth > 0) {
            document.body.style.paddingRight = `${scrollBarWidth}px`;
        }

        return () => {
            document.body.style.overflow = originalStyle;
            document.body.style.paddingRight = originalPaddingRight;
        };
    }, [isLocked]);
}
