

export type StaticNotificationKind = 'site_announcement' | 'greeting';

export interface StaticNotificationDefinition {
  id: string;
  kind: StaticNotificationKind;
  title: string;
  message: string;
  created_at: string;
  // 未来可以扩展 target/userSegment 等字段
}

export interface ResolvedNotificationContext {
  // 预留：后续可以根据用户信息/时间等做个性化过滤
  isFirstVisit?: boolean;
}

/**
 * 静态站点公告与问候语配置。
 *
 * - 仅在前端维护，不依赖后端接口；
 * - 主要用于：
 *   - 欢迎语（例如首次访问时）；
 *   - 站点前后端功能更新说明；
 *   - 临时公告。
 */
export const STATIC_NOTIFICATIONS: StaticNotificationDefinition[] = [
  {
    id: 'greeting-welcome',
    kind: 'greeting',
    title: '欢迎来到 Odysseia 索引站',
    message:
      '这里是 Odysseia 论坛的导航与搜索面板，你可以通过搜索和关注功能快速定位感兴趣的讨论。',
    created_at: '2024-01-01T00:00:00.000Z',
  },
  {
    id: 'site-update-notification-center',
    kind: 'site_announcement',
    title: '通知中心已上线（实验功能）',
    message:
      '现在你可以在左侧「通知中心」里快速查看关注帖子是否有新的更新。后续会逐步加入站点更新公告和更多提示。',
    created_at: '2024-01-10T00:00:00.000Z',
  },
  {
    id: 'site-update-2025-advanced-search',
    kind: 'site_announcement',
    title: '搜索体验与布局全面升级',
    message:
      '本次更新带来了基于 $tag:xxx$ / $author:xxx$ 的高级搜索语法、标签总览页一键跳转搜索、PC 端侧边栏收起/展开，以及通知中心与无缝滚动加载的进一步打磨。欢迎体验，如有问题可在主服相关频道反馈。',
    created_at: '2025-11-16T00:00:00.000Z',
  },
];

/**
 * 根据上下文过滤静态通知。
 *
 * 当前实现比较简单：直接返回全部静态通知。
 * 未来可以根据用户偏好 / 是否首次访问等做更精细的控制。
 */
export function resolveStaticNotifications(
  _context?: ResolvedNotificationContext,
): StaticNotificationDefinition[] {
  return STATIC_NOTIFICATIONS;
}