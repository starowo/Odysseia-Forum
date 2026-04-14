import { Save, Search } from 'lucide-react';

import { PreferenceTagSelector } from '@/features/preferences/components/PreferenceTagSelector';
import type { PreferencesFormValue } from '@/features/preferences/lib/preferencesMapper';
import { FluidDivider } from '@/shared/ui/FluidDivider';

interface ChannelOption {
  id: string;
  name: string;
}

interface MePreferencesSectionProps {
  availablePreferenceTags: string[];
  channelOptions: ChannelOption[];
  form: PreferencesFormValue;
  isDirty: boolean;
  isLoading: boolean;
  isSaving: boolean;
  isSyncing: boolean;
  onSave: () => void;
  onToggleChannel: (channelId: string) => void;
  onUpdateForm: (updater: (prev: PreferencesFormValue) => PreferencesFormValue) => void;
}

export function MePreferencesSection({
  availablePreferenceTags,
  channelOptions,
  form,
  isDirty,
  isLoading,
  isSaving,
  isSyncing,
  onSave,
  onToggleChannel,
  onUpdateForm,
}: MePreferencesSectionProps) {
  return (
    <section className="px-1">
      <FluidDivider label="Preferences" className="mb-8" />
      <div className="mb-6 flex items-center justify-center gap-2 text-center">
        <Search className="h-4 w-4 text-[var(--od-accent)]" />
        <h2 className="od-text-title">发现偏好</h2>
      </div>

      {isLoading ? (
        <p className="od-text-body">正在加载你的偏好设置...</p>
      ) : (
        <div className="space-y-8">
          <div className="space-y-3">
            <p className="text-sm font-medium text-[var(--od-text-primary)]">偏好频道</p>
            <p className="text-sm leading-6 text-[var(--od-text-secondary)]">
              这些频道会在探索和搜索建议里优先生效，这样你就不会看到你不感兴趣的频道内容被推荐啦。
            </p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {channelOptions.map((channel) => {
                const active = form.preferredChannelIds.includes(channel.id);
                return (
                  <button
                    key={channel.id}
                    type="button"
                    onClick={() => onToggleChannel(channel.id)}
                    className={`rounded-2xl border px-4 py-3 text-left text-sm transition-colors ${
                      active
                        ? 'border-[var(--od-accent)]/40 bg-[var(--od-accent)]/8 text-[var(--od-text-primary)] font-od-medium'
                        : 'border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] text-[var(--od-text-secondary)] font-od-normal'
                    }`}
                  >
                    {channel.name}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <label className="block space-y-2">
              <span className="block text-sm font-medium text-[var(--od-text-secondary)]">默认排序</span>
              <select
                value={form.sortMethod}
                onChange={(e) => {
                  onUpdateForm((prev) => ({ ...prev, sortMethod: e.target.value as PreferencesFormValue['sortMethod'] }));
                }}
                className="w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4 py-3 text-sm text-[var(--od-text-primary)]"
              >
                <option value="last_active_desc">最后活跃</option>
                <option value="created_desc">最新发布</option>
                <option value="reaction_desc">点赞热度</option>
                <option value="reply_desc">讨论热度</option>
                <option value="relevance">综合推荐</option>
              </select>
            </label>

            <label className="block space-y-2">
              <span className="block text-sm font-medium text-[var(--od-text-secondary)]">每页条数</span>
              <input
                type="number"
                min={1}
                max={100}
                value={form.resultsPerPage}
                onChange={(e) => {
                  onUpdateForm((prev) => ({ ...prev, resultsPerPage: Number(e.target.value) || 24 }));
                }}
                className="w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4 py-3 text-sm text-[var(--od-text-primary)]"
              />
            </label>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <PreferenceTagSelector
              label="包含标签"
              placeholder="还没有设置正选标签"
              selectedTags={form.includeTagsText.split(',').map((item) => item.trim()).filter(Boolean)}
              availableTags={availablePreferenceTags.filter((tag) => !form.excludeTagsText.split(',').map((item) => item.trim()).filter(Boolean).includes(tag))}
              tone="include"
              onChange={(tags) => {
                onUpdateForm((prev) => ({ ...prev, includeTagsText: tags.join(', ') }));
              }}
            />
            <PreferenceTagSelector
              label="排除标签"
              placeholder="还没有设置反选标签"
              selectedTags={form.excludeTagsText.split(',').map((item) => item.trim()).filter(Boolean)}
              availableTags={availablePreferenceTags.filter((tag) => !form.includeTagsText.split(',').map((item) => item.trim()).filter(Boolean).includes(tag))}
              tone="exclude"
              onChange={(tags) => {
                onUpdateForm((prev) => ({ ...prev, excludeTagsText: tags.join(', ') }));
              }}
            />
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <label className="block space-y-2">
              <span className="block text-sm font-medium text-[var(--od-text-secondary)]">关键词包含</span>
              <textarea
                value={form.includeKeywordsText}
                onChange={(e) => {
                  onUpdateForm((prev) => ({ ...prev, includeKeywordsText: e.target.value }));
                }}
                className="min-h-[110px] w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4 py-3 text-sm text-[var(--od-text-primary)]"
              />
            </label>
            <label className="block space-y-2">
              <span className="block text-sm font-medium text-[var(--od-text-secondary)]">关键词排除</span>
              <textarea
                value={form.excludeKeywordsText}
                onChange={(e) => {
                  onUpdateForm((prev) => ({ ...prev, excludeKeywordsText: e.target.value }));
                }}
                className="min-h-[110px] w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4 py-3 text-sm text-[var(--od-text-primary)]"
              />
            </label>
          </div>

          <div className="rounded-[1.2rem] border border-[color-mix(in_srgb,var(--od-text-secondary)_14%,transparent)] bg-[color-mix(in_srgb,var(--od-surface-input)_56%,transparent)] px-4 py-4 text-sm leading-6 text-[var(--od-text-secondary)]">
            这些偏好主要影响“发现流”，不会偷偷改你的搜索框，也不会压过你手动选的频道。空搜索、全频道探索和搜索建议会参考它们，但你的主动操作始终优先。
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[color-mix(in_srgb,var(--od-text-secondary)_14%,transparent)] pt-5">
            <p className="od-text-meta">
              当前状态：{isSyncing ? '同步中' : isDirty ? '有未保存修改' : '已同步'}
            </p>
            <button
              type="button"
              onClick={onSave}
              disabled={isSaving}
              className="od-inline-action od-inline-action-primary disabled:opacity-60"
            >
              <Save className="h-4 w-4" />
              {isSaving ? '保存中...' : '保存偏好'}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
