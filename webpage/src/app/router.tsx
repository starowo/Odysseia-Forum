import { createBrowserRouter } from 'react-router-dom';
import { LoginPage } from '@/pages/AuthPage/LoginPage';
import { CallbackPage } from '@/pages/AuthPage/CallbackPage';
import { SearchPage } from '@/pages/SearchPage';
import { PlazaPage } from '@/pages/PlazaPage';
import { DrawPage } from '@/pages/DrawPage';
import { TagsPage } from '@/pages/TagsPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { AboutPage } from '@/pages/AboutPage';
import { MePage } from '@/pages/MePage';
import { UserProfilePage } from '@/pages/UserProfilePage';
import { TestPage } from '@/pages/TestPage';
import { BooklistsPage } from '@/pages/BooklistsPage';
import { BooklistDetailPage } from '@/pages/BooklistDetailPage';
import { ProtectedRoute } from '@/app/providers/ProtectedRoute';
import { RootLayout } from '@/widgets/layout/RootLayout';
import { NotFoundPage } from '@/pages/NotFoundPage';

const isDevToolsEnabled = import.meta.env.DEV || import.meta.env.VITE_API_MOCKING === 'true';

const appChildren = [
  {
    index: true,
    element: <PlazaPage />,
  },
  {
    path: 'search',
    element: <SearchPage />,
  },
  {
    path: 'draw',
    element: <DrawPage />,
  },
  {
    path: 'tags',
    element: <TagsPage />,
  },
  {
    path: 'booklists',
    element: <BooklistsPage />,
  },
  {
    path: 'booklists/:id',
    element: <BooklistDetailPage />,
  },
  {
    path: 'settings',
    element: <SettingsPage />,
  },
  {
    path: 'me',
    element: <MePage />,
  },
  {
    path: 'u/:userId',
    element: <UserProfilePage />,
  },
  ...(isDevToolsEnabled
    ? [
      {
        path: 'test',
        element: <TestPage />,
      },
    ]
    : []),
];

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/about',
    element: <AboutPage />,
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
        children: [
          ...appChildren,
          {
            path: '*',
            element: <NotFoundPage />,
          },
        ],
      },
    ],
  },
]);
