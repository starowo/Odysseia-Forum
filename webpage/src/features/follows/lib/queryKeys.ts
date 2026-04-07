export const followsKeys = {
  all: ['follows'] as const,
  list: () => [...followsKeys.all, 'list'] as const,
  unreadCount: () => [...followsKeys.all, 'unread-count'] as const,
  combined: () => [...followsKeys.all, 'combined'] as const,
};
