import {
  Grid,
  Image as ImageIcon,
  ImageOff,
  Layout,
  List,
  Maximize2,
  Minimize2,
  Monitor,
  Scan,
  Type,
  ExternalLink,
  AppWindow,
} from 'lucide-react';

import { themes } from '@/shared/styles/themes';
import type { UserSettings } from '@/shared/lib/settings';

import { themeOptions } from './config';
import { SettingsPageSection } from './SettingsPageSection';

type DisplaySettingsSectionProps = {
  settings: UserSettings;
  updateSettings: (updates: Partial<UserSettings>) => void;
};

export function DisplaySettingsSection({ settings, updateSettings }: DisplaySettingsSectionProps) {
  const inlineChoiceClass = 'od-option-inline';
  const rowChoiceClass = 'od-setting-choice flex items-center gap-3 p-4 text-left';

  return (
    <SettingsPageSection dividerLabel="Display" kicker="Visual Hierarchy" title="显示设置" icon={Layout}>
      <div className="space-y-7">
        <div>
          <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
            阅读尺寸
          </label>
          <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">
            把字体和卡片密度放在一起调，会更容易找到舒服的阅读节奏。
          </p>
          <div className="space-y-4">
            <div>
              <p className="mb-2 text-[0.75rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Font Size</p>
              <div className="od-options-wrap">
                {(['small', 'medium', 'large'] as const).map((size) => {
                  const isActive = settings.fontSize === size;
                  const sampleSizeClass =
                    size === 'small' ? 'text-xs' : size === 'medium' ? 'text-sm' : 'text-lg';

                  return (
                    <button
                      key={size}
                      type="button"
                      onClick={() => updateSettings({ fontSize: size })}
                      data-active={isActive}
                      className={`${inlineChoiceClass} min-w-[5rem] justify-center`}
                    >
                      <span
                        className={`od-choice-value font-semibold leading-none ${sampleSizeClass} ${
                          isActive ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'
                        }`}
                      >
                        Aa
                      </span>
                      <span
                        className={`od-choice-title text-sm ${
                          isActive ? 'font-medium text-[var(--od-text-primary)]' : 'text-[var(--od-text-primary)]'
                        }`}
                      >
                        {size === 'small' ? '小' : size === 'medium' ? '中' : '大'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <p className="mb-2 text-[0.75rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Card Density</p>
              <div className="od-options-wrap">
                {(['compact', 'normal', 'large'] as const).map((size) => {
                  const isActive = settings.cardSize === size;
                  const Icon = size === 'compact' ? Minimize2 : size === 'normal' ? Scan : Maximize2;

                  return (
                    <button
                      key={size}
                      type="button"
                      onClick={() => updateSettings({ cardSize: size })}
                      data-active={isActive}
                      className={`${inlineChoiceClass} min-w-[6rem] justify-center`}
                    >
                      <Icon
                        className={`od-choice-icon h-5 w-5 ${
                          isActive ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'
                        }`}
                      />
                      <span
                        className={`od-choice-title text-sm ${
                          isActive ? 'font-medium text-[var(--od-text-primary)]' : 'text-[var(--od-text-primary)]'
                        }`}
                      >
                        {size === 'compact' ? '紧凑' : size === 'normal' ? '标准' : '宽松'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
            字体来源
          </label>
          <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">
            有些主题自带好看的字体，开启后我会帮你自动加载；关掉就回到系统默认字体。
          </p>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <button
              type="button"
              onClick={() => updateSettings({ fontMode: 'system' })}
              data-active={settings.fontMode === 'system'}
              className={`${rowChoiceClass} ${settings.fontMode === 'system' ? '' : ''}`}
            >
              <Monitor className={`od-choice-icon h-5 w-5 ${settings.fontMode === 'system' ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
              <div className="text-left">
                <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">系统字体</div>
                <div className="text-xs text-[var(--od-text-tertiary)]">最快、最稳，保持设备默认阅读习惯</div>
              </div>
            </button>
            <button
              type="button"
              onClick={() => updateSettings({ fontMode: 'theme' })}
              data-active={settings.fontMode === 'theme'}
              className={`${rowChoiceClass} ${settings.fontMode === 'theme' ? '' : ''}`}
            >
              <Type className={`od-choice-icon h-5 w-5 ${settings.fontMode === 'theme' ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
              <div className="text-left">
                <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">主题字体</div>
                <div className="text-xs text-[var(--od-text-tertiary)]">自动加载主题附带字体，让主题不仅换色也换字形</div>
              </div>
            </button>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
            布局与图片
          </label>
          <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">
            网格更偏视觉浏览，列表更偏高效筛选；图片则决定内容流是更有氛围还是更专注文案。
          </p>
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <button
                type="button"
                onClick={() => updateSettings({ layoutMode: 'grid' })}
                data-active={settings.layoutMode === 'grid'}
                className={`${rowChoiceClass} ${settings.layoutMode === 'grid' ? '' : ''}`}
              >
                <Grid className={`od-choice-icon h-5 w-5 ${settings.layoutMode === 'grid' ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
                <div className="text-left">
                  <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">网格布局</div>
                  <div className="text-xs text-[var(--od-text-tertiary)]">适合广场、封面、视觉浏览</div>
                </div>
              </button>
              <button
                type="button"
                onClick={() => updateSettings({ layoutMode: 'list' })}
                data-active={settings.layoutMode === 'list'}
                className={`${rowChoiceClass} ${settings.layoutMode === 'list' ? '' : ''}`}
              >
                <List className={`od-choice-icon h-5 w-5 ${settings.layoutMode === 'list' ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
                <div className="text-left">
                  <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">列表布局</div>
                  <div className="text-xs text-[var(--od-text-tertiary)]">适合搜索、筛选和连续阅读</div>
                </div>
              </button>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <button
                type="button"
                onClick={() => updateSettings({ imageMode: 'normal' })}
                data-active={settings.imageMode === 'normal'}
                className={`${rowChoiceClass} ${settings.imageMode === 'normal' ? '' : ''}`}
              >
                <ImageIcon className={`od-choice-icon h-5 w-5 ${settings.imageMode === 'normal' ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
                <div className="text-left">
                  <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">正常加载</div>
                  <div className="text-xs text-[var(--od-text-tertiary)]">显示缩略图，更完整也更有情绪氛围</div>
                </div>
              </button>
              <button
                type="button"
                onClick={() => updateSettings({ imageMode: 'off' })}
                data-active={settings.imageMode === 'off'}
                className={`${rowChoiceClass} ${settings.imageMode === 'off' ? '' : ''}`}
              >
                <ImageOff className={`od-choice-icon h-5 w-5 ${settings.imageMode === 'off' ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
                <div className="text-left">
                  <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">关闭图片</div>
                  <div className="text-xs text-[var(--od-text-tertiary)]">更纯粹，也更省流</div>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div>
           <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
             端外跳转方式
           </label>
           <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">
             选择打开 Discord 帖子时，是唤起本地客户端还是在网页端打开。
           </p>
           <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
             <button
               type="button"
               onClick={() => updateSettings({ openMode: 'app' })}
               data-active={settings.openMode === 'app'}
               className={`${rowChoiceClass} ${settings.openMode === 'app' ? '' : ''}`}
             >
               <AppWindow className={`od-choice-icon h-5 w-5 ${settings.openMode === 'app' ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
               <div className="text-left">
                 <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">Discord 客户端</div>
                 <div className="text-xs text-[var(--od-text-tertiary)]">使用 discord:// 协议直接唤起 App</div>
               </div>
             </button>
             <button
               type="button"
               onClick={() => updateSettings({ openMode: 'web' })}
               data-active={settings.openMode === 'web'}
               className={`${rowChoiceClass} ${settings.openMode === 'web' ? '' : ''}`}
             >
               <ExternalLink className={`od-choice-icon h-5 w-5 ${settings.openMode === 'web' ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
               <div className="text-left">
                 <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">网页版</div>
                 <div className="text-xs text-[var(--od-text-tertiary)]">在当前浏览器新标签页中打开</div>
               </div>
             </button>
           </div>
        </div>

        <div>
          <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
            主题氛围
          </label>
          <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">
            每套主题都是成组的色彩与字形方案，不只是单纯换个底色。
          </p>
          <div className="space-y-2">
            {themeOptions.map((option) => {
              const isSelected = settings.theme === option.id;
              const themeColors = option.themeKey ? themes[option.themeKey].colors : null;

              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => updateSettings({ theme: option.id })}
                  data-active={isSelected}
                  className={`${rowChoiceClass} w-full justify-between`}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <option.icon className={`od-choice-icon h-5 w-5 ${isSelected ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-secondary)]'}`} />
                    <div className="flex min-w-0 flex-col text-left">
                      <span className="od-choice-title text-xs text-[var(--od-text-primary)]">{option.label}</span>
                      <span className="truncate text-[10px] text-[var(--od-text-tertiary)]">{option.description}</span>
                    </div>
                  </div>
                  {themeColors && (
                    <div className="ml-3 flex shrink-0 gap-1.5">
                      <span className="h-4 w-4 rounded-full border border-black/10" style={{ background: themeColors.background }} />
                      <span className="h-4 w-4 rounded-full border border-black/10" style={{ background: themeColors.card }} />
                      <span className="h-4 w-4 rounded-full border border-black/10" style={{ background: themeColors.accent }} />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </SettingsPageSection>
  );
}
