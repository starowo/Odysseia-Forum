import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type { Thread } from '@/types/thread.types';

interface DevMockState {
  threads: Thread[];
  followed_ids: string[];
  updated_ids: string[];
}

export function TestPage() {
  const [token, setToken] = useState<string | null>(null);
  const isMocking = import.meta.env.VITE_API_MOCKING === 'true';
  const queryClient = useQueryClient();

  useEffect(() => {
    try {
      setToken(localStorage.getItem('auth_token'));
    } catch {
      setToken(null);
    }
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ['dev', 'mock', 'state'],
    queryFn: async () => {
      const res = await apiClient.get<DevMockState>('/dev/mock/state');
      return res.data;
    },
    enabled: isMocking,
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post('/dev/mock/reset', {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dev', 'mock', 'state'] });
    },
  });

  const addThreadMutation = useMutation({
    mutationFn: async (opts: { follow?: boolean; has_update?: boolean }) => {
      await apiClient.post('/dev/mock/add-thread', {
        follow: opts.follow,
        has_update: opts.has_update,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dev', 'mock', 'state'] });
    },
  });

  const markRandomUpdateMutation = useMutation({
    mutationFn: async () => {
      const followed = data?.followed_ids ?? [];
      if (!followed.length) return;
      const target = followed[Math.floor(Math.random() * followed.length)];
      await apiClient.post('/dev/mock/mark-update', { thread_id: target, has_update: true });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dev', 'mock', 'state'] });
    },
  });

  const hasToken = !!token;
  const addPending = addThreadMutation.status === 'pending';
  const markPending = markRandomUpdateMutation.status === 'pending';
  const resetPending = resetMutation.status === 'pending';

  return (
    <div className="min-h-screen bg-[var(--od-bg)] px-6 py-6 text-[var(--od-text-primary)]">
      <h1 className="mb-6 text-2xl font-bold">开发模式测试页面</h1>

      {/* 环境信息 */}
      <div className="space-y-3 rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 text-sm">
        <div>
          <span className="font-semibold">API Mocking：</span>
          <span>{isMocking ? '✅ 已启用（MSW）' : '❌ 未启用'}</span>
        </div>
        <div>
          <span className="font-semibold">有 Token：</span>
          <span>{hasToken ? '✅ 是' : '❌ 否'}</span>
        </div>
        <div>
          <span className="font-semibold">Token 值：</span>
          <pre className="mt-2 max-h-24 overflow-auto rounded bg-[var(--od-bg-secondary)] p-2 text-xs">
            {token || 'none'}
          </pre>
        </div>
        {!isMocking && (
          <p className="mt-2 text-xs text-[var(--od-text-tertiary)]">
            提示：只有在本地开发并启用 VITE_API_MOCKING=true 时，下方的 Mock 控制台才会工作。
          </p>
        )}
      </div>

      {/* Mock 状态总览 + 动作面板 */}
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="space-y-3 rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 text-sm">
          <h2 className="text-sm font-semibold">Mock 数据总览</h2>
          {isMocking ? (
            isLoading || !data ? (
              <p className="text-[var(--od-text-tertiary)]">加载中…</p>
            ) : (
              <>
                <p>总帖子数：{data.threads.length}</p>
                <p>已关注：{data.followed_ids.length}</p>
                <p>有更新的关注：{data.updated_ids.length}</p>
              </>
            )
          ) : (
            <p className="text-[var(--od-text-tertiary)]">Mock 未启用。</p>
          )}
        </div>

        <div className="space-y-3 rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-4 text-sm">
          <h2 className="text-sm font-semibold">快速动作</h2>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={!isMocking || addPending}
              onClick={() => addThreadMutation.mutate({})}
              className="rounded bg-[var(--od-accent)] px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              新增随机帖子
            </button>
            <button
              type="button"
              disabled={!isMocking || addPending}
              onClick={() => addThreadMutation.mutate({ follow: true })}
              className="rounded bg-[var(--od-accent)] px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              新增并关注
            </button>
            <button
              type="button"
              disabled={!isMocking || !data?.followed_ids.length || markPending}
              onClick={() => markRandomUpdateMutation.mutate()}
              className="rounded bg-amber-500 px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              随机关注帖标记有更新
            </button>
            <button
              type="button"
              disabled={!isMocking || resetPending}
              onClick={() => resetMutation.mutate()}
              className="rounded bg-red-500 px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              重置 Mock 数据
            </button>
          </div>
          <p className="mt-1 text-[10px] text-[var(--od-text-tertiary)]">
            所有操作都会直接影响 /v1/search、/v1/follows、/v1/follows/unread-count 等接口返回的数据结构，
            用于模拟真实生产环境的数据流。
          </p>
        </div>
      </div>
    </div>
  );
}
