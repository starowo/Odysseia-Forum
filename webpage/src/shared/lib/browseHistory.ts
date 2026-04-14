import type { Thread } from '@/entities/thread/types';

const BROWSE_HISTORY_KEY = 'odysseia_browse_history';
const MAX_BROWSE_HISTORY_ITEMS = 50;

export interface BrowseHistoryItem {
  threadId: string;
  title: string;
  channelId?: string;
  authorName?: string;
  thumbnailUrl?: string | null;
  visitedAt: number;
}

function normalizeBrowseHistoryItem(raw: unknown): BrowseHistoryItem | null {
  if (!raw || typeof raw !== 'object') return null;

  const record = raw as Record<string, unknown>;
  const threadId = typeof record.threadId === 'string' ? record.threadId.trim() : '';
  const title = typeof record.title === 'string' ? record.title.trim() : '';

  if (!threadId || !title) return null;

  return {
    threadId,
    title,
    channelId: typeof record.channelId === 'string' && record.channelId.trim() ? record.channelId.trim() : undefined,
    authorName: typeof record.authorName === 'string' && record.authorName.trim() ? record.authorName.trim() : undefined,
    thumbnailUrl: typeof record.thumbnailUrl === 'string' ? record.thumbnailUrl : null,
    visitedAt: typeof record.visitedAt === 'number' && Number.isFinite(record.visitedAt) ? record.visitedAt : Date.now(),
  };
}

function saveBrowseHistory(items: BrowseHistoryItem[]) {
  localStorage.setItem(BROWSE_HISTORY_KEY, JSON.stringify(items));
}

export function getBrowseHistory(): BrowseHistoryItem[] {
  try {
    const raw = localStorage.getItem(BROWSE_HISTORY_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed
      .map((item) => normalizeBrowseHistoryItem(item))
      .filter((item): item is BrowseHistoryItem => Boolean(item))
      .sort((a, b) => b.visitedAt - a.visitedAt)
      .slice(0, MAX_BROWSE_HISTORY_ITEMS);
  } catch (error) {
    console.error('Failed to load browse history:', error);
    return [];
  }
}

export function addBrowseHistory(thread: Thread): void {
  const threadId = String(thread.thread_id || '').trim();
  const title = String(thread.title || '').trim();
  if (!threadId || !title) return;

  try {
    const nextItem: BrowseHistoryItem = {
      threadId,
      title,
      channelId: thread.channel_id ? String(thread.channel_id) : undefined,
      authorName: thread.author?.display_name || thread.author?.global_name || thread.author?.name || undefined,
      thumbnailUrl: thread.thumbnail_urls?.[0] || null,
      visitedAt: Date.now(),
    };

    const history = getBrowseHistory();
    const filtered = history.filter((item) => item.threadId !== threadId);
    saveBrowseHistory([nextItem, ...filtered].slice(0, MAX_BROWSE_HISTORY_ITEMS));
  } catch (error) {
    console.error('Failed to save browse history:', error);
  }
}

export function removeBrowseHistory(threadId: string) {
  try {
    const history = getBrowseHistory().filter((item) => item.threadId !== threadId);
    saveBrowseHistory(history);
  } catch (error) {
    console.error('Failed to remove browse history:', error);
  }
}

export function clearBrowseHistory() {
  try {
    localStorage.removeItem(BROWSE_HISTORY_KEY);
  } catch (error) {
    console.error('Failed to clear browse history:', error);
  }
}
