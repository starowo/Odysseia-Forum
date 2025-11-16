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

const isDevToolsEnabled = import.meta.env.DEV || import.meta.env.VITE_API_MOCKING === 'true';

const appChildren = [
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
  ...(isDevToolsEnabled
    ? [
        {
          path: 'test',
          element: <TestPage />,
        },
      ]
    : []),
  {
    path: 'about',
    element: <AboutPage />,
  },
];

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
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <RootLayout />,
        children: appChildren,
      },
    ],
  },
]);
