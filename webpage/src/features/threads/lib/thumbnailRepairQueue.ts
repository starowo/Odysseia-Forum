import type { QueryClient } from '@tanstack/react-query';

import { fetchImagesApi, type FetchImageItem } from '@/features/threads/api/fetchImagesApi';

type ThumbnailListener = (urls: string[]) => void;

interface BrokenThumbnailPayload {
  threadId: string | number;
  channelId?: string | number;
}

const FLUSH_DELAY_MS = 800;
const MAX_BATCH_SIZE = 20;
const FAILURE_COOLDOWN_MS = 30 * 1000;

let boundQueryClient: QueryClient | null = null;
let flushTimer: number | null = null;
const pending = new Map<string, FetchImageItem>();
const repaired = new Map<string, string[]>();
const failureCooldown = new Map<string, number>();
const listeners = new Map<string, Set<ThumbnailListener>>();

function toThreadId(value: string | number): string {
  return String(value).trim();
}

function toChannelId(value?: string | number): number | undefined {
  if (value === undefined || value === null || value === '') return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function patchThreadThumbnailsInData(data: unknown, threadId: string, urls: string[]): unknown {
  if (!data) return data;

  if (Array.isArray(data)) {
    let changed = false;
    const next = data.map((item) => {
      const patched = patchThreadThumbnailsInData(item, threadId, urls);
      if (patched !== item) changed = true;
      return patched;
    });
    return changed ? next : data;
  }

  if (typeof data !== 'object') return data;

  const record = data as Record<string, unknown>;
  let changed = false;
  const nextRecord: Record<string, unknown> = { ...record };

  if (String(record.thread_id ?? '') === threadId) {
    nextRecord.thumbnail_urls = urls;
    changed = true;
  }

  for (const [key, value] of Object.entries(record)) {
    const patched = patchThreadThumbnailsInData(value, threadId, urls);
    if (patched !== value) {
      nextRecord[key] = patched;
      changed = true;
    }
  }

  return changed ? nextRecord : data;
}

function patchQueryCaches(threadId: string, urls: string[]) {
  if (!boundQueryClient) return;
  const allQueries = boundQueryClient.getQueryCache().getAll();

  for (const query of allQueries) {
    const queryKey = query.queryKey;
    boundQueryClient.setQueryData(queryKey, (oldData: unknown) => {
      return patchThreadThumbnailsInData(oldData, threadId, urls);
    });
  }
}

function notify(threadId: string, urls: string[]) {
  const group = listeners.get(threadId);
  if (!group || group.size === 0) return;
  for (const handler of group) {
    handler(urls);
  }
}

async function flushQueue() {
  flushTimer = null;
  if (pending.size === 0) return;

  const items = Array.from(pending.values()).slice(0, MAX_BATCH_SIZE);
  for (const item of items) {
    pending.delete(String(item.thread_id));
  }

  try {
    const response = await fetchImagesApi.refresh(items);
    for (const result of response.results || []) {
      const threadId = toThreadId(result.thread_id);
      if (!result.thumbnail_urls || result.thumbnail_urls.length === 0) continue;
      repaired.set(threadId, result.thumbnail_urls);
      patchQueryCaches(threadId, result.thumbnail_urls);
      notify(threadId, result.thumbnail_urls);
    }
  } catch {
    const cooldownUntil = Date.now() + FAILURE_COOLDOWN_MS;
    for (const item of items) {
      failureCooldown.set(String(item.thread_id), cooldownUntil);
    }
  }

  if (pending.size > 0) {
    scheduleFlush();
  }
}

function scheduleFlush() {
  if (flushTimer !== null) return;
  flushTimer = window.setTimeout(() => {
    void flushQueue();
  }, FLUSH_DELAY_MS);
}

export function bindThumbnailRepairQueryClient(queryClient: QueryClient) {
  boundQueryClient = queryClient;
}

export function reportBrokenThreadThumbnail(payload: BrokenThumbnailPayload) {
  const threadId = toThreadId(payload.threadId);
  if (!threadId || !/^\d+$/.test(threadId)) return;

  const cooldownUntil = failureCooldown.get(threadId) || 0;
  if (cooldownUntil > Date.now()) return;

  if (pending.has(threadId)) return;

  pending.set(threadId, {
    thread_id: Number(threadId),
    channel_id: toChannelId(payload.channelId),
  });

  scheduleFlush();
}

export function getRepairedThumbnail(threadId: string | number) {
  return repaired.get(toThreadId(threadId)) || null;
}

export function subscribeThreadThumbnailRepair(
  threadId: string | number,
  handler: ThumbnailListener,
) {
  const key = toThreadId(threadId);
  const group = listeners.get(key) || new Set<ThumbnailListener>();
  group.add(handler);
  listeners.set(key, group);

  return () => {
    const current = listeners.get(key);
    if (!current) return;
    current.delete(handler);
    if (current.size === 0) listeners.delete(key);
  };
}
