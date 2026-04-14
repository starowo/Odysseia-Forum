import { useEffect } from 'react';
import { QueryClient, QueryClientProvider, QueryCache } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { RouterProvider } from 'react-router-dom';
import { Toaster } from 'sonner';
import { ErrorBoundary } from '@/app/providers/ErrorBoundary';
import { showMascotErrorToast } from '@/features/mascot/lib/mascotToast';
import { ThemeProvider } from '@/app/themes/ThemeProvider';
import { bindThumbnailRepairQueryClient } from '@/features/threads/lib/thumbnailRepairQueue';
import { consumeAuthTokenFromHash } from '@/shared/lib/authSession';
import { router } from './router';
import { useMascotStore } from '@/features/mascot/store/mascotStore';

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      console.error('Global Query Error:', error);
      showMascotErrorToast('network', { id: 'global-network-error' });
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      retry: 1,
    },
  },
});

// 方便调试
if (import.meta.env.DEV) {
  (window as any).queryClient = queryClient;
}

export function App() {
  useEffect(() => {
    bindThumbnailRepairQueryClient(queryClient);
  }, []);

  useEffect(() => {
    const mascotStore = useMascotStore.getState();
    if (!mascotStore.hasWelcomed) {
      mascotStore.reset();
      mascotStore.markWelcomed();
    }

    const token = consumeAuthTokenFromHash();
    if (token) {
      // Invalidate auth queries to load user data
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    }
  }, []);

  // Monitor network status
  useEffect(() => {
    const handleOffline = () => {
      showMascotErrorToast('network', { id: 'browser-offline-error' });
    };

    window.addEventListener('offline', handleOffline);
    return () => window.removeEventListener('offline', handleOffline);
  }, []);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <RouterProvider router={router} />
          <Toaster
            position="top-center"
            richColors
            visibleToasts={4}
            expand={false}
            gap={14}
            toastOptions={{
              style: {
                background: 'color-mix(in srgb, var(--od-bg-secondary) 82%, transparent)',
                backdropFilter: 'blur(16px) saturate(122%)',
                WebkitBackdropFilter: 'blur(16px) saturate(122%)',
                border: '1px solid var(--od-glass-border)',
                color: 'var(--od-text-primary)',
                boxShadow: 'var(--od-shadow-floating)',
              },
            }}
          />
          {/* 仅在需要调试时显示 DevTools，默认隐藏 */}
          {import.meta.env.VITE_SHOW_DEVTOOLS === 'true' && (
            <ReactQueryDevtools initialIsOpen={false} />
          )}
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
