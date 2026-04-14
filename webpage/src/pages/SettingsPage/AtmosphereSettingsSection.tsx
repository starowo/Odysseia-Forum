import { EyeOff, Sparkles } from 'lucide-react';
import { useMemo } from 'react';

import type { UserSettings } from '@/shared/lib/settings';

import { backgroundPresets } from './config';
import { SettingsPageSection } from './SettingsPageSection';
import { SettingsToggle } from './SettingsToggle';

type AtmosphereSettingsSectionProps = {
  settings: UserSettings;
  opacityDraft: number;
  blurDraft: number;
  onOpacityDraftChange: (value: number) => void;
  onBlurDraftChange: (value: number) => void;
  onCommitOpacity: () => void;
  onCommitBlur: () => void;
  onUploadBackground: (file: File | null) => void;
  onClearBackgroundImage: () => void;
  updateSettings: (updates: Partial<UserSettings>) => void;
};

export function AtmosphereSettingsSection({
  settings,
  opacityDraft,
  blurDraft,
  onOpacityDraftChange,
  onBlurDraftChange,
  onCommitOpacity,
  onCommitBlur,
  onUploadBackground,
  onClearBackgroundImage,
  updateSettings,
}: AtmosphereSettingsSectionProps) {
  const currentWallpaper = useMemo(
    () => settings.backgroundImageBase64 || settings.backgroundImageUrl,
    [settings.backgroundImageBase64, settings.backgroundImageUrl],
  );

  const currentSourceLabel = settings.backgroundImageBase64
    ? '本地上传（base64）'
    : settings.backgroundImageUrl
      ? '外链 URL'
      : '未设置';

  const glassEnabled = settings.glassMode !== 'off';

  return (
    <SettingsPageSection dividerLabel="Atmosphere" kicker="Backdrop Mood" title="背景与毛玻璃" icon={Sparkles}>
      <div className="space-y-6">
        <div className="od-setting-subsection space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">背景图</p>
              <p className="mt-2 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">
                图片资源和启用状态分开处理。你可以先存一张图，再决定要不要现在打开。
              </p>
            </div>
            <SettingsToggle
              checked={settings.backgroundImageEnabled}
              onToggle={() => updateSettings({ backgroundImageEnabled: !settings.backgroundImageEnabled })}
              ariaLabel="切换背景图"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)]">
            <div className="space-y-4">
              <div className="od-setting-panel-soft">
                <p className="mb-2 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Presets</p>
                <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">先选一张喜欢的底图，再微调透明度和磨砂感。</p>
                <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                  {backgroundPresets.map((preset) => {
                    const isSelected = settings.backgroundImageUrl === preset.previewUrl && settings.backgroundImageEnabled;

                    return (
                      <button
                        key={preset.id}
                        type="button"
                        onClick={() =>
                          updateSettings({
                            backgroundImageEnabled: true,
                            backgroundImageUrl: preset.previewUrl,
                            backgroundImageBase64: '',
                          })
                        }
                        data-active={isSelected}
                        className="od-setting-choice flex flex-col items-start gap-2 overflow-hidden rounded-[1.15rem] p-2 text-left"
                      >
                        <span
                          className="h-24 w-full rounded-[0.95rem] bg-cover bg-center"
                          style={{ backgroundImage: `url(${preset.previewUrl})` }}
                        />
                        <span className="text-sm font-medium text-[var(--od-text-primary)]">{preset.label}</span>
                        <span className="text-[0.72rem] text-[var(--od-text-tertiary)]">{preset.description}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <label className="block">
                <span className="mb-1 block text-base font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">本地上传</span>
                <span className="mb-2 block text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">直接从本地选张图，最大 5MB，会保存在你的浏览器里。</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => onUploadBackground(e.target.files?.[0] || null)}
                  className="w-full cursor-pointer rounded-2xl border border-[var(--od-shell-line)] bg-[var(--od-surface-input)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-base font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">背景图 URL</span>
                <span className="mb-2 block text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">也可以贴一个外部图片链接，换起来更方便。</span>
                <input
                  type="text"
                  value={settings.backgroundImageUrl}
                  placeholder="https://..."
                  onChange={(e) =>
                    updateSettings({
                      backgroundImageUrl: e.target.value.trim(),
                      backgroundImageBase64: '',
                    })
                  }
                  className="w-full rounded-2xl border border-[var(--od-shell-line)] bg-[var(--od-surface-input)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                />
              </label>
            </div>

            <div className="space-y-4">
              <div className="overflow-hidden rounded-[1.3rem] border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)]">
                <div className="relative h-52 w-full overflow-hidden">
                  {currentWallpaper ? (
                    <>
                      <div
                        className="absolute inset-0 bg-cover bg-center"
                        style={{ backgroundImage: `url(${currentWallpaper})`, opacity: Math.max(0.18, opacityDraft / 100) }}
                      />
                      <div className="absolute inset-0 bg-[linear-gradient(180deg,transparent_0%,color-mix(in_srgb,var(--od-bg)_68%,transparent)_100%)]" />
                      <div className="absolute inset-x-0 bottom-0 p-4">
                        <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-white/70">Preview</p>
                        <p className="mt-1 text-base font-semibold text-white">{settings.backgroundImageEnabled ? '当前背景已启用' : '背景已保存，当前未启用'}</p>
                        <p className="mt-1 text-xs leading-[1.5] text-white/78">透明度 {opacityDraft}% · 磨砂 {blurDraft}px · {currentSourceLabel}</p>
                      </div>
                    </>
                  ) : (
                    <div className="flex h-full items-center justify-center px-6 text-center text-sm leading-[1.6] text-[var(--od-text-secondary)]">
                      这里会显示当前背景图预览。先选预设图、上传本地图片，或者贴一个 URL 过来。
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between gap-3 border-t border-[var(--od-shell-line)] px-4 py-3">
                  <span className="truncate text-[0.84rem] font-semibold leading-[1.35] text-[var(--od-text-emphasis)]">当前来源：{currentSourceLabel}</span>
                  <button type="button" onClick={onClearBackgroundImage} className="od-inline-action od-inline-action-ghost px-3 py-1">
                    清除背景图
                  </button>
                </div>
              </div>

              <div className="od-setting-row">
                <div>
                  <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">毛玻璃</p>
                  <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">先用总开关决定是否启用，再选自动还是强制开启。</p>
                </div>
                <SettingsToggle
                  checked={glassEnabled}
                  onToggle={() => updateSettings({ glassMode: glassEnabled ? 'off' : 'auto' })}
                  ariaLabel="切换毛玻璃"
                />
              </div>

              <div>
                <p className="mb-2 text-[0.75rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Glass Strategy</p>
                <div className="od-options-wrap">
                  {([
                    ['auto', '自动'],
                    ['on', '始终开启'],
                    ['off', '关闭'],
                  ] as const).map(([mode, label]) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => updateSettings({ glassMode: mode })}
                      data-active={settings.glassMode === mode}
                      className="od-option-inline"
                    >
                      <span className="od-choice-title text-sm text-[var(--od-text-primary)]">{label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="od-setting-row">
                <div>
                  <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">无背景色模式</p>
                  <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">去掉页面大面积底色，只保留文字、分隔和结构线。</p>
                </div>
                <SettingsToggle
                  checked={settings.backgroundlessMode}
                  onToggle={() => updateSettings({ backgroundlessMode: !settings.backgroundlessMode })}
                  ariaLabel="切换无背景色模式"
                />
              </div>

              <div className="flex items-start gap-3 rounded-[1.1rem] border border-[var(--od-shell-line)]/70 bg-[color-mix(in_srgb,var(--od-surface-input)_78%,transparent)] px-4 py-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">
                <EyeOff className="mt-0.5 h-4 w-4 shrink-0 text-[var(--od-text-emphasis)]" />
                <p>放心，这个开关只影响页面大背景。弹窗、下拉框这些浮层还是保持实心的，不会看不清。</p>
              </div>

              <label className="block">
                <span className="mb-2 flex items-center justify-between text-sm font-medium text-[var(--od-text-secondary)]">
                  <span>背景图透明度</span>
                  <span className="text-[0.88rem] font-bold leading-[1.3] text-[var(--od-text-value)]">{opacityDraft}%</span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={1}
                  value={opacityDraft}
                  onChange={(e) => onOpacityDraftChange(Number(e.target.value))}
                  onMouseUp={onCommitOpacity}
                  onTouchEnd={onCommitOpacity}
                  onKeyUp={onCommitOpacity}
                  className="w-full accent-[var(--od-accent)]"
                />
              </label>

              <label className="block">
                <span className="mb-2 flex items-center justify-between text-sm font-medium text-[var(--od-text-secondary)]">
                  <span>磨砂强度（Blur）</span>
                  <span className="text-[0.88rem] font-bold leading-[1.3] text-[var(--od-text-value)]">{blurDraft}px</span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={32}
                  step={1}
                  value={blurDraft}
                  onChange={(e) => onBlurDraftChange(Number(e.target.value))}
                  onMouseUp={onCommitBlur}
                  onTouchEnd={onCommitBlur}
                  onKeyUp={onCommitBlur}
                  className="w-full accent-[var(--od-accent)]"
                />
              </label>
            </div>
          </div>
        </div>

        <div className="od-setting-row">
          <div>
            <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">紧凑模式</p>
            <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">收紧界面间距，列表和卡片会更贴近，适合偏高密度的信息浏览。</p>
          </div>
          <SettingsToggle
            checked={settings.compactMode}
            onToggle={() => updateSettings({ compactMode: !settings.compactMode })}
            ariaLabel="切换紧凑模式"
          />
        </div>
      </div>
    </SettingsPageSection>
  );
}
