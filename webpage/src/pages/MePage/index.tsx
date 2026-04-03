import { useEffect, useMemo, useState } from 'react';
import { UserRound, Save, SlidersHorizontal, Search, Image as ImageIcon } from 'lucide-react';
import { toast } from 'sonner';

import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
import {
  toPreferencesFormValue,
  toPreferencesUpdatePayload,
  type PreferencesFormValue,
} from '@/features/preferences/lib/preferencesMapper';
import { CHANNEL_CATEGORIES } from '@/shared/config/navigation';
import { GUILD_ID } from '@/shared/config/channelCategories.private';

const DEFAULT_FORM: PreferencesFormValue = {
  preferredChannelIds: [],
  includeTagsText: '',
  excludeTagsText: '',
  includeKeywordsText: '',
  excludeKeywordsText: '',
  previewImageMode: 'thumbnail',
  resultsPerPage: 24,
  sortMethod: 'last_active_desc',
};

export function MePage() {
  const {
    user,
    preferences,
    isLoading,
    isFetching,
    savePreferences,
    isSaving,
  } = useUserPreferences({ guildId: GUILD_ID });

  const [form, setForm] = useState<PreferencesFormValue>(DEFAULT_FORM);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (isDirty) return;
    setForm(toPreferencesFormValue(preferences));
  }, [preferences, isDirty]);

  const channelOptions = useMemo(
    () => CHANNEL_CATEGORIES.flatMap((group) => group.channels),
    [],
  );

  const toggleChannel = (channelId: string) => {
    setIsDirty(true);
    setForm((prev) => {
      const exists = prev.preferredChannelIds.includes(channelId);
      return {
        ...prev,
        preferredChannelIds: exists
          ? prev.preferredChannelIds.filter((id) => id !== channelId)
          : [...prev.preferredChannelIds, channelId],
      };
    });
  };

  const save = async () => {
    try {
      const payload = toPreferencesUpdatePayload(form);
      await savePreferences(payload);
      setIsDirty(false);
      toast.success('偏好已保存');
    } catch {
      toast.error('保存偏好失败');
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-5">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--od-accent)]/12 text-[var(--od-accent)]">
            <UserRound className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">我的</h1>
            <p className="text-sm text-[var(--od-text-secondary)]">账号信息与搜索偏好管理</p>
          </div>
        </div>

        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-xl bg-[var(--od-bg-secondary)] p-3">
            <p className="text-[var(--od-text-tertiary)]">昵称</p>
            <p className="mt-1 font-semibold text-[var(--od-text-primary)]">
              {user?.global_name || user?.username || '未登录'}
            </p>
          </div>
          <div className="rounded-xl bg-[var(--od-bg-secondary)] p-3">
            <p className="text-[var(--od-text-tertiary)]">用户 ID</p>
            <p className="mt-1 font-mono text-[var(--od-text-primary)]">{user?.id || '-'}</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-5">
        <div className="mb-4 flex items-center gap-2">
          <Search className="h-4 w-4 text-[var(--od-accent)]" />
          <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">搜索偏好</h2>
        </div>

        {isLoading ? (
          <p className="text-sm text-[var(--od-text-secondary)]">加载偏好中...</p>
        ) : (
          <div className="space-y-5">
            <div>
              <p className="mb-2 text-sm font-medium text-[var(--od-text-secondary)]">偏好频道</p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {channelOptions.map((channel) => {
                  const active = form.preferredChannelIds.includes(channel.id);
                  return (
                    <button
                      key={channel.id}
                      type="button"
                      onClick={() => toggleChannel(channel.id)}
                      className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                        active
                          ? 'border-[var(--od-accent)] bg-[var(--od-accent)]/10 text-[var(--od-text-primary)]'
                          : 'border-[var(--od-border)] bg-[var(--od-bg-secondary)] text-[var(--od-text-secondary)]'
                      }`}
                    >
                      {channel.name}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">默认排序</span>
                <select
                  value={form.sortMethod}
                  onChange={(e) => {
                    setIsDirty(true);
                    setForm((prev) => ({ ...prev, sortMethod: e.target.value as PreferencesFormValue['sortMethod'] }));
                  }}
                  className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                >
                  <option value="last_active_desc">最后活跃</option>
                  <option value="created_desc">最新发布</option>
                  <option value="reaction_desc">点赞热度</option>
                  <option value="reply_desc">讨论热度</option>
                  <option value="relevance">综合推荐</option>
                </select>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">每页条数</span>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={form.resultsPerPage}
                  onChange={(e) => {
                    setIsDirty(true);
                    setForm((prev) => ({ ...prev, resultsPerPage: Number(e.target.value) || 24 }));
                  }}
                  className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                />
              </label>
            </div>

            <div>
              <p className="mb-2 inline-flex items-center gap-2 text-sm font-medium text-[var(--od-text-secondary)]">
                <ImageIcon className="h-4 w-4" />
                预览图片模式
              </p>
              <div className="grid gap-2 sm:grid-cols-3">
                {(
                  [
                    { value: 'thumbnail', label: '缩略图' },
                    { value: 'full', label: '完整图' },
                    { value: 'none', label: '不显示' },
                  ] as const
                ).map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => {
                      setIsDirty(true);
                      setForm((prev) => ({ ...prev, previewImageMode: item.value }));
                    }}
                    className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                      form.previewImageMode === item.value
                        ? 'border-[var(--od-accent)] bg-[var(--od-accent)]/10 text-[var(--od-text-primary)]'
                        : 'border-[var(--od-border)] bg-[var(--od-bg-secondary)] text-[var(--od-text-secondary)]'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">包含标签（逗号分隔）</span>
                <input
                  type="text"
                  value={form.includeTagsText}
                  onChange={(e) => {
                    setIsDirty(true);
                    setForm((prev) => ({ ...prev, includeTagsText: e.target.value }));
                  }}
                  className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                  placeholder="例如：剧情, 科幻"
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">排除标签（逗号分隔）</span>
                <input
                  type="text"
                  value={form.excludeTagsText}
                  onChange={(e) => {
                    setIsDirty(true);
                    setForm((prev) => ({ ...prev, excludeTagsText: e.target.value }));
                  }}
                  className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                  placeholder="例如：广告, 测试"
                />
              </label>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">关键词包含</span>
                <textarea
                  value={form.includeKeywordsText}
                  onChange={(e) => {
                    setIsDirty(true);
                    setForm((prev) => ({ ...prev, includeKeywordsText: e.target.value }));
                  }}
                  className="min-h-[88px] w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">关键词排除</span>
                <textarea
                  value={form.excludeKeywordsText}
                  onChange={(e) => {
                    setIsDirty(true);
                    setForm((prev) => ({ ...prev, excludeKeywordsText: e.target.value }));
                  }}
                  className="min-h-[88px] w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                />
              </label>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--od-border)] bg-[var(--od-bg-secondary)] p-3">
              <p className="text-xs text-[var(--od-text-tertiary)]">
                当前状态：{isFetching ? '同步中' : isDirty ? '有未保存修改' : '已同步'}
              </p>
              <button
                type="button"
                onClick={save}
                disabled={isSaving}
                className="inline-flex items-center gap-2 rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                <Save className="h-4 w-4" />
                {isSaving ? '保存中...' : '保存偏好'}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-[var(--od-border)] bg-[var(--od-card)] p-5">
        <div className="mb-2 inline-flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-[var(--od-accent)]" />
          <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">说明</h2>
        </div>
        <p className="text-sm text-[var(--od-text-secondary)]">
          这里保存的是账号级搜索偏好，会影响首次进入搜索页时的默认参数。主题、字体、布局等设备显示设置请在“设置”页面调整。
        </p>
      </div>
    </div>
  );
}
