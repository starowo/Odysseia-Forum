import {
  Settings,
  Moon,
  Sun,
  Monitor,
  Bell,
  Layout,
  Grid,
  List,
  Image as ImageIcon,
  ImageOff,
  SlidersHorizontal,
  Info,
  Minimize2,
  Scan,
  Maximize2,
  Type,
  EyeOff,
} from 'lucide-react';

import { useSettings } from '@/shared/hooks/useSettings';
import { resetUserSettings } from '@/shared/lib/settings';
import { notifyError, notifySuccess } from '@/shared/lib/notify';
import { themes } from '@/shared/styles/themes';
import { APP_VERSION } from '@/shared/config/appInfo';
import defaultWinterBackground from '@/assets/images/background/winter.png';
import defaultSpringBackground from '@/assets/images/background/spring.png';
import defaultSpring2Background from '@/assets/images/background/spring2.png';
import defaultBannerBackground from '@/assets/images/banners/adfd891a-f9f7-4f9d-8d7c-975fb32a7f0d.png';
import { useEffect, useState } from 'react';
import { FluidDivider } from '@/shared/ui/FluidDivider';

export function SettingsPage() {
  const { settings, updateSettings } = useSettings();
  const [opacityDraft, setOpacityDraft] = useState(Math.round(settings.backgroundImageOpacity * 100));
  const [blurDraft, setBlurDraft] = useState(Math.round(settings.glassBlur));
  const inlineChoiceClass = (active: boolean) =>
    `od-option-inline ${active ? '' : ''}`;
  const rowChoiceClass = (active: boolean) =>
    `od-setting-choice flex items-center gap-3 p-4 text-left ${active ? '' : ''}`;

  useEffect(() => {
    setOpacityDraft(Math.round(settings.backgroundImageOpacity * 100));
  }, [settings.backgroundImageOpacity]);

  useEffect(() => {
    setBlurDraft(Math.round(settings.glassBlur));
  }, [settings.glassBlur]);

  const handleUploadBackground = (file: File | null) => {
    if (!file) return;

    const maxBytes = 5 * 1024 * 1024;
    if (file.size > maxBytes) {
      notifyError('图片超过 5MB，无法保存到本地');
      return;
    }

    if (!file.type.startsWith('image/')) {
      notifyError('仅支持图片文件');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : '';
      if (!result.startsWith('data:image/')) {
        notifyError('图片读取失败，请重试');
        return;
      }

      // base64 膨胀后通常比原文件大约 33%，同时 localStorage 容量也通常只有 ~5MB
      if (result.length > 4_500_000) {
        notifyError('base64 体积过大，建议改用 URL 或内置背景图');
        return;
      }

      try {
        updateSettings({
          backgroundImageBase64: result,
          backgroundImageUrl: '',
          backgroundImageEnabled: true,
        });
        notifySuccess('本地背景图已保存（base64）');
      } catch {
        notifyError('保存失败，可能是本地存储空间不足');
      }
    };
    reader.onerror = () => notifyError('读取图片失败');
    reader.readAsDataURL(file);
  };

  const clearBackgroundImage = () => {
    updateSettings({
      backgroundImageEnabled: false,
      backgroundImageUrl: '',
      backgroundImageBase64: '',
    });
    notifySuccess('背景图已清除');
  };

  const themeOptions = [
    {
      id: 'discord-dark' as const,
      label: 'Discord 深色',
      icon: Moon,
      themeKey: 'discordDark' as const,
      description: '经典 Discord 暗色风格',
    },
    {
      id: 'discord-light' as const,
      label: 'Discord 浅色',
      icon: Sun,
      themeKey: 'discordLight' as const,
      description: '明亮的浅色主题',
    },
    {
      id: 'claude-dark' as const,
      label: 'Claude 深色',
      icon: Moon,
      themeKey: 'claudeDark' as const,
      description: '保留的经典深色主题',
    },
    {
      id: 'catppuccin' as const,
      label: 'Catppuccin',
      icon: Moon,
      themeKey: 'catppuccin' as const,
      description: '柔和高对比的社区经典',
    },
    {
      id: 'nord' as const,
      label: 'Nord',
      icon: Moon,
      themeKey: 'nord' as const,
      description: '冷调清晰的信息密度风格',
    },
    {
      id: 'everforest' as const,
      label: 'Everforest',
      icon: Moon,
      themeKey: 'everforest' as const,
      description: '护眼森林调，适合长时阅读',
    },
    {
      id: 'sakura-day' as const,
      label: 'Sakura Day',
      icon: Sun,
      themeKey: 'sakuraDay' as const,
      description: '春樱明朝风，淡粉与叶绿',
    },
    {
      id: 'yozakura-night' as const,
      label: 'Yozakura Night',
      icon: Moon,
      themeKey: 'yozakuraNight' as const,
      description: '夜樱霓光，冷调紫与冰蓝',
    },
    {
      id: 'tokyo-night' as const,
      label: 'Tokyo Night',
      icon: Moon,
      themeKey: 'tokyoNight' as const,
      description: '代码高亮感最强的夜色主题',
    },
    {
      id: 'auto' as const,
      label: '跟随系统',
      icon: Monitor,
      themeKey: null,
      description: '根据系统深浅色自动切换',
    },
  ];

  const handleResetSettings = () => {
    if (confirm('确定要重置所有设置为默认值吗？')) {
      resetUserSettings();
      notifySuccess('设置已重置为默认值');
      setTimeout(() => window.location.reload(), 1000);
    }
  };

  return (
    <>
      <div className="px-4 py-4 text-[var(--od-text-primary)] sm:px-6 lg:px-8">
        {/* 标题栏 */}
        <div className="px-1 py-3">
          <div className="flex items-center gap-4">
            <Settings className="h-6 w-6 shrink-0 text-[var(--od-accent)]" />
            <div>
              <p className="mb-2 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Personal Workspace</p>
              <h1 className="od-section-title">设置</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)]">这里是你的专属调色板，我帮你把所有显示偏好都收拢在一起了。随便调，调完马上生效哦～</p>
            </div>
          </div>
        </div>

        {/* 设置内容 */}
        <div className="mt-4 space-y-10 px-1">
          {/* 显示设置 */}
          <div className="od-setting-section">
            <FluidDivider label="Display" tone="strong" className="mb-5" />
            <div className="mb-4 flex items-center gap-3">
              <Layout className="od-choice-icon h-5 w-5 text-[var(--od-text-secondary)]" />
              <div>
                <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Visual Hierarchy</p>
                <h2 className="od-section-title mt-1">显示设置</h2>
              </div>
            </div>

            <div className="space-y-6">
              {/* 字体大小 */}
              <div>
                <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
                  字体大小
                </label>
                <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">字号差异拉大一点，阅读节奏会更清楚～大胆试试看，不喜欢随时改回来。</p>
                <div className="od-options-wrap">
                  {(['small', 'medium', 'large'] as const).map((size) => {
                    const isActive = settings.fontSize === size;
                    const sampleSizeClass =
                      size === 'small' ? 'text-xs' : size === 'medium' ? 'text-sm' : 'text-lg';

                    return (
                      <button
                        key={size}
                        onClick={() => updateSettings({ fontSize: size })}
                        data-active={isActive}
                        className={`${inlineChoiceClass(isActive)} min-w-[5rem] justify-center`}
                      >
                        {/* 用不同字号的 Aa 代替图标，让差异更直观 */}
                        <span
                          className={`od-choice-value font-semibold leading-none ${sampleSizeClass} ${isActive
                            ? 'text-[var(--od-accent)]'
                            : 'text-[var(--od-text-secondary)]'
                            }`}
                        >
                          Aa
                        </span>
                        <span
                          className={`od-choice-title text-sm ${isActive
                            ? 'text-[var(--od-text-primary)] font-medium'
                            : 'text-[var(--od-text-primary)]'
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
                <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
                  字体来源
                </label>
                <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">有些主题自带好看的字体，开启后我会帮你自动加载～关掉就回到系统默认字体。</p>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <button
                    onClick={() => updateSettings({ fontMode: 'system' })}
                    data-active={settings.fontMode === 'system'}
                    className={rowChoiceClass(settings.fontMode === 'system')}
                  >
                    <Monitor
                      className={`od-choice-icon h-5 w-5 ${settings.fontMode === 'system'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">系统字体</div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">最快、最稳，保持设备默认阅读习惯</div>
                    </div>
                  </button>
                  <button
                    onClick={() => updateSettings({ fontMode: 'theme' })}
                    data-active={settings.fontMode === 'theme'}
                    className={rowChoiceClass(settings.fontMode === 'theme')}
                  >
                    <Type
                      className={`od-choice-icon h-5 w-5 ${settings.fontMode === 'theme'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">主题字体</div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">自动加载主题附带的 CDN 字体，让主题不仅换色也换字形</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* 卡片大小 */}
              <div>
                <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
                  卡片大小
                </label>
                <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">控制卡片的呼吸感，会影响广场、搜索和个人页的整体节奏。放大了看着更舒服。</p>
                <div className="od-options-wrap">
                  {(['compact', 'normal', 'large'] as const).map((size) => {
                    const isActive = settings.cardSize === size;
                    const Icon =
                      size === 'compact' ? Minimize2 : size === 'normal' ? Scan : Maximize2;

                    return (
                      <button
                        key={size}
                        onClick={() => updateSettings({ cardSize: size })}
                        data-active={isActive}
                        className={`${inlineChoiceClass(isActive)} min-w-[6rem] justify-center`}
                      >
                        <Icon
                          className={`od-choice-icon h-5 w-5 ${isActive
                            ? 'text-[var(--od-accent)]'
                            : 'text-[var(--od-text-secondary)]'
                            }`}
                        />
                        <span
                          className={`od-choice-title text-sm ${isActive
                            ? 'text-[var(--od-text-primary)] font-medium'
                            : 'text-[var(--od-text-primary)]'
                            }`}
                        >
                          {size === 'compact' ? '紧凑' : size === 'normal' ? '标准' : '宽松'}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 布局模式 */}
              <div>
                <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
                  布局模式
                </label>
                <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">网格更有封面感，列表更适合高效筛选。看你今天想怎么逛～</p>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <button
                    onClick={() => updateSettings({ layoutMode: 'grid' })}
                    data-active={settings.layoutMode === 'grid'}
                    className={rowChoiceClass(settings.layoutMode === 'grid')}
                  >
                    <Grid
                      className={`od-choice-icon h-5 w-5 ${settings.layoutMode === 'grid'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">
                        网格布局
                      </div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">卡片式显示</div>
                      <div className="mt-1 text-[0.84rem] font-semibold leading-[1.35] text-[var(--od-text-emphasis)]">适合广场、封面、视觉浏览</div>
                    </div>
                  </button>
                  <button
                    onClick={() => updateSettings({ layoutMode: 'list' })}
                    data-active={settings.layoutMode === 'list'}
                    className={rowChoiceClass(settings.layoutMode === 'list')}
                  >
                    <List
                      className={`od-choice-icon h-5 w-5 ${settings.layoutMode === 'list'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">
                        列表布局
                      </div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">紧凑列表显示</div>
                      <div className="mt-1 text-[0.84rem] font-semibold leading-[1.35] text-[var(--od-text-emphasis)]">适合搜索、筛选和连续阅读</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* 图片加载模式 */}
              <div>
                <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
                  图片加载
                </label>
                <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">图片可以帮你记住内容，关掉的话切换成纯文字流，加载更快，也更专注。</p>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <button
                    onClick={() => updateSettings({ imageMode: 'normal' })}
                    data-active={settings.imageMode === 'normal'}
                    className={rowChoiceClass(settings.imageMode === 'normal')}
                  >
                    <ImageIcon
                      className={`od-choice-icon h-5 w-5 ${settings.imageMode === 'normal'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">
                        正常加载
                      </div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">
                        显示帖子缩略图等图片（默认）
                      </div>
                      <div className="mt-1 text-[0.84rem] font-semibold leading-[1.35] text-[var(--od-text-emphasis)]">更完整，也更有情绪氛围</div>
                    </div>
                  </button>
                  <button
                    onClick={() => updateSettings({ imageMode: 'off' })}
                    data-active={settings.imageMode === 'off'}
                    className={rowChoiceClass(settings.imageMode === 'off')}
                  >
                    <ImageOff
                      className={`od-choice-icon h-5 w-5 ${settings.imageMode === 'off'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="od-choice-title text-sm font-medium text-[var(--od-text-primary)]">
                        关闭图片（省流）
                      </div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">
                        不再请求帖子缩略图等图片，适合流量有限或弱网环境
                      </div>
                      <div className="mt-1 text-[0.84rem] font-semibold leading-[1.35] text-[var(--od-text-emphasis)]">更纯粹，也更专注文字信息</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* 主题选择 */}
              <div>
                <label className="mb-1 block text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">
                  主题
                </label>
                <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">每套主题都是精心调配的一整套色彩氛围，不只是换个底色哦～试试看哪个最合你心意。</p>
                <div className="space-y-2">
                  {themeOptions.map((option) => {
                    const isSelected = settings.theme === option.id;
                    const themeColors =
                      option.themeKey && option.themeKey in themes
                        ? themes[option.themeKey].colors
                        : null;

                    return (
                      <button
                        key={option.id}
                        onClick={() => updateSettings({ theme: option.id })}
                        data-active={isSelected}
                        className={`${rowChoiceClass(isSelected)} w-full justify-between`}
                      >
                        <div className="flex min-w-0 items-center gap-3">
                            <option.icon
                              className={`od-choice-icon h-5 w-5 ${isSelected
                                ? 'text-[var(--od-accent)]'
                                : 'text-[var(--od-text-secondary)]'
                                }`}
                            />
                            <div className="flex min-w-0 flex-col text-left">
                              <span className="od-choice-title text-xs text-[var(--od-text-primary)]">
                                {option.label}
                              </span>
                              <span className="truncate text-[10px] text-[var(--od-text-tertiary)]">
                                {option.description}
                              </span>
                            </div>
                        </div>
                        {option.id !== 'auto' && themeColors && (
                          <div className="ml-3 flex shrink-0 gap-1.5">
                            <span
                              className="h-4 w-4 rounded-full border border-black/10"
                              style={{ background: themeColors.background }}
                            />
                            <span
                              className="h-4 w-4 rounded-full border border-black/10"
                              style={{ background: themeColors.card }}
                            />
                            <span
                              className="h-4 w-4 rounded-full border border-black/10"
                              style={{ background: themeColors.accent }}
                            />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="od-setting-subsection space-y-3">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Atmosphere</p>
                    <p className="mt-1 text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">背景图与毛玻璃</p>
                    <p className="mt-2 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">背景图和毛玻璃是连在一起的～没有背景图时自动降级成普通模式，浮层始终保持清晰可读。</p>
                  </div>
                  <button
                    onClick={() =>
                      updateSettings({ backgroundImageEnabled: !settings.backgroundImageEnabled })
                    }
                    data-checked={settings.backgroundImageEnabled || Boolean(settings.backgroundImageUrl) || Boolean(settings.backgroundImageBase64)}
                    className="od-toggle"
                  >
                    <div className="od-toggle-thumb" />
                  </button>
                </div>

                <div className="space-y-3">
                  <div className="od-setting-panel-soft">
                    <p className="mb-2 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Presets</p>
                    <p className="mb-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">先选一张喜欢的底图，然后调调透明度和模糊就好。</p>
                    <div className="od-options-wrap">
                      <button
                        type="button"
                        onClick={() =>
                          updateSettings({
                            backgroundImageEnabled: true,
                            backgroundImageUrl: defaultWinterBackground,
                            backgroundImageBase64: '',
                          })
                        }
                          className="od-option-inline text-left text-xs text-[var(--od-text-primary)]"
                      >
                        Winter（内置）
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          updateSettings({
                            backgroundImageEnabled: true,
                            backgroundImageUrl: defaultSpringBackground,
                            backgroundImageBase64: '',
                          })
                        }
                          className="od-option-inline text-left text-xs text-[var(--od-text-primary)]"
                      >
                        Spring（内置）
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          updateSettings({
                            backgroundImageEnabled: true,
                            backgroundImageUrl: defaultSpring2Background,
                            backgroundImageBase64: '',
                          })
                        }
                          className="od-option-inline text-left text-xs text-[var(--od-text-primary)]"
                      >
                        Spring 2（内置）
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          updateSettings({
                            backgroundImageEnabled: true,
                            backgroundImageUrl: defaultBannerBackground,
                            backgroundImageBase64: '',
                          })
                        }
                          className="od-option-inline text-left text-xs text-[var(--od-text-primary)]"
                      >
                        Banner（内置）
                      </button>
                    </div>
                  </div>

                  <label className="block">
                    <span className="mb-1 block text-base font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">本地上传</span>
                    <span className="mb-2 block text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">直接从本地选张图，最大 5MB，会保存在你的浏览器里。</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => handleUploadBackground(e.target.files?.[0] || null)}
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

                  <div className="od-setting-row">
                    <span className="truncate text-[0.84rem] font-semibold leading-[1.35] text-[var(--od-text-emphasis)]">
                      当前来源：
                      {settings.backgroundImageBase64
                        ? '本地上传(base64)'
                        : settings.backgroundImageUrl
                          ? '外链 URL'
                          : '未设置'}
                    </span>
                    <button
                      type="button"
                      onClick={clearBackgroundImage}
                      className="od-inline-action od-inline-action-ghost px-3 py-1"
                    >
                      清除背景图
                    </button>
                  </div>

                  <label className="block">
                    <span className="mb-1 block text-base font-semibold tracking-[-0.02em] text-[var(--od-text-primary)]">毛玻璃模式</span>
                    <span className="mb-2 block text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">有背景图的时候，要不要让页面稍微模糊一点。</span>
                    <select
                      value={settings.glassMode}
                      onChange={(e) =>
                        updateSettings({ glassMode: e.target.value as 'off' | 'on' | 'auto' })
                      }
                      className="w-full rounded-2xl border border-[var(--od-shell-line)] bg-[var(--od-surface-input)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    >
                      <option value="off">关闭</option>
                      <option value="on">开启</option>
                      <option value="auto">自动</option>
                    </select>
                  </label>

                  <div className="od-setting-row">
                    <div>
                      <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">无背景色模式</p>
                      <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">去掉页面大面积的底色，只保留文字和结构线。滑杆还是有效的，只是叠的是一层暗色而不是面板底色。</p>
                    </div>
                    <button
                      onClick={() => updateSettings({ backgroundlessMode: !settings.backgroundlessMode })}
                      data-checked={settings.backgroundlessMode}
                      className="od-toggle"
                    >
                      <div className="od-toggle-thumb" />
                    </button>
                  </div>

                  <div className="flex items-start gap-3 rounded-[1.1rem] border border-[var(--od-shell-line)]/70 bg-[color-mix(in_srgb,var(--od-surface-input)_78%,transparent)] px-4 py-3 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">
                    <EyeOff className="mt-0.5 h-4 w-4 shrink-0 text-[var(--od-text-emphasis)]" />
                    <p>放心，这个开关只影响页面大背景，弹窗、下拉框那些浮层还是保持实心的，不会看不清。</p>
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
                      onChange={(e) => setOpacityDraft(Number(e.target.value))}
                      onMouseUp={() => updateSettings({ backgroundImageOpacity: opacityDraft / 100 })}
                      onTouchEnd={() => updateSettings({ backgroundImageOpacity: opacityDraft / 100 })}
                      onKeyUp={() => updateSettings({ backgroundImageOpacity: opacityDraft / 100 })}
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
                      onChange={(e) => setBlurDraft(Number(e.target.value))}
                      onMouseUp={() => updateSettings({ glassBlur: blurDraft })}
                      onTouchEnd={() => updateSettings({ glassBlur: blurDraft })}
                      onKeyUp={() => updateSettings({ glassBlur: blurDraft })}
                      className="w-full accent-[var(--od-accent)]"
                    />
                  </label>
                </div>
              </div>

              {/* 紧凑模式 */}
              <div className="od-setting-row">
                <div>
                  <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">紧凑模式</p>
                  <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">收紧界面间距，列表和卡片看起来更紧凑，适合喜欢高密度信息的你。</p>
                </div>
                <button
                  onClick={() => updateSettings({ compactMode: !settings.compactMode })}
                  data-checked={settings.compactMode}
                  className="od-toggle"
                >
                  <div className="od-toggle-thumb" />
                </button>
              </div>
            </div>
          </div>



          {/* 通知设置 */}
          <div className="od-setting-section">
            <FluidDivider label="Notifications" tone="strong" className="mb-5" />
            <div className="mb-4 flex items-center gap-3">
              <Bell className="od-choice-icon h-5 w-5 text-[var(--od-text-secondary)]" />
              <div>
                <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Signals</p>
                <h2 className="od-section-title mt-1">通知</h2>
              </div>
            </div>

            <div className="space-y-3">
              <div className="od-setting-row">
                <div>
                  <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">新帖通知</p>
                  <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">关注的频道有新帖了，我会第一时间告诉你。</p>
                </div>
                <button
                  onClick={() =>
                    updateSettings({
                      notifications: {
                        ...settings.notifications,
                        newPosts: !settings.notifications.newPosts,
                      },
                    })
                  }
                  data-checked={settings.notifications.newPosts}
                  className="od-toggle"
                >
                  <div className="od-toggle-thumb" />
                </button>
              </div>

              <div className="od-setting-row">
                <div>
                  <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">回复通知</p>
                  <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">有人回复了你的帖子，我会提醒你过去看看。</p>
                </div>
                <button
                  onClick={() =>
                    updateSettings({
                      notifications: {
                        ...settings.notifications,
                        replies: !settings.notifications.replies,
                      },
                    })
                  }
                  data-checked={settings.notifications.replies}
                  className="od-toggle"
                >
                  <div className="od-toggle-thumb" />
                </button>
              </div>

              <div className="od-setting-row">
                <div>
                  <p className="od-choice-title text-base font-semibold text-[var(--od-text-primary)]">提及通知</p>
                  <p className="mt-1 text-[0.82rem] leading-[1.55] text-[var(--od-text-secondary)]">有人 @ 了你，可能在找你聊天哦。</p>
                </div>
                <button
                  onClick={() =>
                    updateSettings({
                      notifications: {
                        ...settings.notifications,
                        mentions: !settings.notifications.mentions,
                      },
                    })
                  }
                  data-checked={settings.notifications.mentions}
                  className="od-toggle"
                >
                  <div className="od-toggle-thumb" />
                </button>
              </div>
            </div>
          </div>

          {/* 高级设置 */}
          <div className="od-setting-section">
            <FluidDivider label="Advanced" tone="strong" className="mb-5" />
            <div className="mb-4 flex items-center gap-3">
              <SlidersHorizontal className="od-choice-icon h-5 w-5 text-[var(--od-text-secondary)]" />
              <div>
                <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Safety</p>
                <h2 className="od-section-title mt-1">高级</h2>
              </div>
            </div>

            <button
              onClick={handleResetSettings}
              className="w-full rounded-[1.1rem] bg-[var(--od-error)] p-4 text-left transition-colors hover:bg-[color-mix(in_oklab,var(--od-error)_85%,black)]"
            >
              <div className="text-sm font-medium text-white">重置设置</div>
              <div className="text-xs text-red-200">把所有设置恢复到最初的样子，确定要来一次大扫除吗？</div>
            </button>
          </div>

          {/* 版本与更新 */}
          <div className="od-setting-section">
            <FluidDivider label="Version" tone="strong" className="mb-5" />
            <div className="mb-3 flex items-center gap-3">
              <Info className="od-choice-icon h-5 w-5 text-[var(--od-text-secondary)]" />
              <div>
                <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--od-text-label)]">Release Notes</p>
                <h2 className="od-section-title mt-1">版本与更新</h2>
              </div>
            </div>
            <p className="text-sm text-[var(--od-text-secondary)]">
              当前前端版本：
              <span className="ml-1 font-mono text-[var(--od-text-emphasis)]">{APP_VERSION}</span>
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-[var(--od-text-tertiary)]">
              <li>新增帖子预览浮层与 Markdown 展示体验</li>
              <li>改进搜索筛选与列表/网格视图切换</li>
              <li>优化登出、Mock 环境与错误提示的健壮性</li>
            </ul>
          </div>

          {/* 提示信息 */}
          <div className="rounded-[1.3rem] bg-[color-mix(in_oklab,var(--od-accent)_8%,transparent)] p-4">
            <p className="text-sm text-[var(--od-text-secondary)]">
              💡 <span className="font-medium text-[var(--od-text-primary)]">小提醒：</span>
              你的设置都保存在本地浏览器里～清除浏览器数据的话，这些设置也会一起消失哦。
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
