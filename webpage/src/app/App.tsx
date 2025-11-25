import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { RouterProvider } from 'react-router-dom';
import { Toaster } from 'sonner';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ThemeProvider } from '../components/layout/ThemeProvider';
import { router } from './router';
import { FloatingBanner } from '@/features/banner/components/FloatingBanner';

const queryClient = new QueryClient({
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
  // Extract token from URL hash (iOS/Worker compatibility)
  useEffect(() => {
    const hash = window.location.hash;
    const match = hash.match(/[#&]token=([^&]+)/);
    if (match) {
      const token = match[1];
      localStorage.setItem('auth_token', token);
      window.location.hash = ''; // Clean URL
      // Invalidate auth queries to load user data
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    }
  }, []);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <RouterProvider router={router} />
          <FloatingBanner />
          <Toaster position="top-center" richColors />
          {/* 仅在需要调试时显示 DevTools，默认隐藏 */}
          {import.meta.env.VITE_SHOW_DEVTOOLS === 'true' && (
            <ReactQueryDevtools initialIsOpen={false} />
          )}
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
