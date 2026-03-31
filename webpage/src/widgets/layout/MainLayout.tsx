/**
 * MainLayout — 已弃用
 *
 * V2 架构下，布局由 RootLayout (AppShell) 统一提供。
 * 此文件保留仅为向后兼容，新页面不应再使用。
 */
import { ReactNode } from 'react';

interface MainLayoutProps {
  children: ReactNode;
  showTopBar?: boolean;
}

/** @deprecated 请使用 AppShell (RootLayout) 代替 */
export function MainLayout({ children }: MainLayoutProps) {
  // V2: 直接渲染 children，布局由 AppShell 提供
  return <>{children}</>;
}
