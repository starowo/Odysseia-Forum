import { createBrowserRouter } from 'react-router-dom';
import { LoginPage } from '@/pages/AuthPage/LoginPage';
import { CallbackPage } from '@/pages/AuthPage/CallbackPage';
import { SearchPage } from '@/pages/SearchPage';
import { FollowsPage } from '@/pages/FollowsPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { AboutPage } from '@/pages/AboutPage';
import { TestPage } from '@/pages/TestPage';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { RootLayout } from '@/components/layout/RootLayout';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/auth/callback',
    element: <CallbackPage />,
  },
  {
    path: '/test',
    element: <TestPage />,
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <RootLayout />,
        children: [
          {
            index: true,
            element: <SearchPage />,
          },
          {
            path: 'follows',
            element: <FollowsPage />,
          },
          {
            path: 'settings',
            element: <SettingsPage />,
          },
          {
            path: 'about',
            element: <AboutPage />,
          },
        ],
      },
    ],
  },
]);
