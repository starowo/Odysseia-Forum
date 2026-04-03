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
} from 'lucide-react';

import { useSettings } from '@/shared/hooks/useSettings';
import { resetUserSettings } from '@/shared/lib/settings';
import { toast } from 'sonner';
import { themes } from '@/shared/styles/themes';
import { APP_VERSION } from '@/shared/config/appInfo';
import defaultWinterBackground from '@/assets/images/background/winter.png';
import defaultSpringBackground from '@/assets/images/background/spring.png';
import defaultSpring2Background from '@/assets/images/background/spring2.png';
import defaultBannerBackground from '@/assets/images/banners/adfd891a-f9f7-4f9d-8d7c-975fb32a7f0d.png';
import { useEffect, useState } from 'react';

export function SettingsPage() {
  const { settings, updateSettings } = useSettings();
  const [opacityDraft, setOpacityDraft] = useState(Math.round(settings.backgroundImageOpacity * 100));
  const [blurDraft, setBlurDraft] = useState(Math.round(settings.glassBlur));

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
      toast.error('图片超过 5MB，无法保存到本地');
      return;
    }

    if (!file.type.startsWith('image/')) {
      toast.error('仅支持图片文件');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : '';
      if (!result.startsWith('data:image/')) {
        toast.error('图片读取失败，请重试');
        return;
      }

      // base64 膨胀后通常比原文件大约 33%，同时 localStorage 容量也通常只有 ~5MB
      if (result.length > 4_500_000) {
        toast.error('base64 体积过大，建议改用 URL 或内置背景图');
        return;
      }

      try {
        updateSettings({
          backgroundImageBase64: result,
          backgroundImageUrl: '',
          backgroundImageEnabled: true,
        });
        toast.success('本地背景图已保存（base64）');
      } catch {
        toast.error('保存失败，可能是本地存储空间不足');
      }
    };
    reader.onerror = () => toast.error('读取图片失败');
    reader.readAsDataURL(file);
  };

  const clearBackgroundImage = () => {
    updateSettings({
      backgroundImageEnabled: false,
      backgroundImageUrl: '',
      backgroundImageBase64: '',
    });
    toast.success('背景图已清除');
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
      toast.success('设置已重置为默认值');
      setTimeout(() => window.location.reload(), 1000);
    }
  };

  return (
    <>
      <div className="text-[var(--od-text-primary)]">
        {/* 标题栏 */}
        <div className="od-fluid-panel border-b px-4 py-4">
          <div className="flex items-center gap-3">
            <Settings className="h-6 w-6 text-[var(--od-text-primary)]" />
            <div>
              <h1 className="text-xl font-bold text-[var(--od-text-primary)]">设置</h1>
              <p className="text-sm text-[var(--od-text-secondary)]">个性化你的体验</p>
            </div>
          </div>
        </div>

        {/* 设置内容 */}
        <div className="space-y-4 p-4">
          {/* 显示设置 */}
          <div className="od-fluid-panel rounded-xl p-6">
            <div className="mb-4 flex items-center gap-3">
              <Layout className="h-5 w-5 text-[var(--od-accent)]" />
              <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">显示设置</h2>
            </div>

            <div className="space-y-6">
              {/* 字体大小 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[var(--od-text-secondary)]">
                  字体大小
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {(['small', 'medium', 'large'] as const).map((size) => {
                    const isActive = settings.fontSize === size;
                    const sampleSizeClass =
                      size === 'small' ? 'text-xs' : size === 'medium' ? 'text-sm' : 'text-lg';

                    return (
                      <button
                        key={size}
                        onClick={() => updateSettings({ fontSize: size })}
                        className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${isActive
                          ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                          : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                          }`}
                      >
                        {/* 用不同字号的 Aa 代替图标，让差异更直观 */}
                        <span
                          className={`font-semibold leading-none ${sampleSizeClass} ${isActive
                            ? 'text-[var(--od-accent)]'
                            : 'text-[var(--od-text-secondary)]'
                            }`}
                        >
                          Aa
                        </span>
                        <span
                          className={`text-sm ${isActive
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

              {/* 卡片大小 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[var(--od-text-secondary)]">
                  卡片大小
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {(['compact', 'normal', 'large'] as const).map((size) => {
                    const isActive = settings.cardSize === size;
                    const Icon =
                      size === 'compact' ? Minimize2 : size === 'normal' ? Scan : Maximize2;

                    return (
                      <button
                        key={size}
                        onClick={() => updateSettings({ cardSize: size })}
                        className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${isActive
                          ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                          : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                          }`}
                      >
                        <Icon
                          className={`h-5 w-5 ${isActive
                            ? 'text-[var(--od-accent)]'
                            : 'text-[var(--od-text-secondary)]'
                            }`}
                        />
                        <span
                          className={`text-sm ${isActive
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
                <label className="mb-3 block text-sm font-medium text-[var(--od-text-secondary)]">
                  布局模式
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => updateSettings({ layoutMode: 'grid' })}
                    className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-all ${settings.layoutMode === 'grid'
                      ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                      : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                      }`}
                  >
                    <Grid
                      className={`h-5 w-5 ${settings.layoutMode === 'grid'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="text-sm font-medium text-[var(--od-text-primary)]">
                        网格布局
                      </div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">卡片式显示</div>
                    </div>
                  </button>
                  <button
                    onClick={() => updateSettings({ layoutMode: 'list' })}
                    className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-all ${settings.layoutMode === 'list'
                      ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                      : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                      }`}
                  >
                    <List
                      className={`h-5 w-5 ${settings.layoutMode === 'list'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="text-sm font-medium text-[var(--od-text-primary)]">
                        列表布局
                      </div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">紧凑列表显示</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* 图片加载模式 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[var(--od-text-secondary)]">
                  图片加载
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => updateSettings({ imageMode: 'normal' })}
                    className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-all ${settings.imageMode === 'normal'
                      ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                      : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                      }`}
                  >
                    <ImageIcon
                      className={`h-5 w-5 ${settings.imageMode === 'normal'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="text-sm font-medium text-[var(--od-text-primary)]">
                        正常加载
                      </div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">
                        显示帖子缩略图等图片（默认）
                      </div>
                    </div>
                  </button>
                  <button
                    onClick={() => updateSettings({ imageMode: 'off' })}
                    className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-all ${settings.imageMode === 'off'
                      ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                      : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                      }`}
                  >
                    <ImageOff
                      className={`h-5 w-5 ${settings.imageMode === 'off'
                        ? 'text-[var(--od-accent)]'
                        : 'text-[var(--od-text-secondary)]'
                        }`}
                    />
                    <div className="text-left">
                      <div className="text-sm font-medium text-[var(--od-text-primary)]">
                        关闭图片（省流）
                      </div>
                      <div className="text-xs text-[var(--od-text-tertiary)]">
                        不再请求帖子缩略图等图片，适合流量有限或弱网环境
                      </div>
                    </div>
                  </button>
                </div>
              </div>

              {/* 主题选择 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[var(--od-text-secondary)]">
                  主题
                </label>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
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
                        className={`flex flex-col gap-2 rounded-lg border-2 p-3 text-left transition-all ${isSelected
                          ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                          : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                          }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <option.icon
                              className={`h-5 w-5 ${isSelected
                                ? 'text-[var(--od-accent)]'
                                : 'text-[var(--od-text-secondary)]'
                                }`}
                            />
                            <div className="flex flex-col">
                              <span className="text-xs text-[var(--od-text-primary)]">
                                {option.label}
                              </span>
                              <span className="text-[10px] text-[var(--od-text-tertiary)]">
                                {option.description}
                              </span>
                            </div>
                          </div>
                          {option.id !== 'auto' && themeColors && (
                            <div className="flex gap-1.5">
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
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="od-fluid-panel rounded-xl p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="od-text-label">背景图与毛玻璃</p>
                    <p className="od-text-meta mt-1">背景图与毛玻璃联动：无背景图时自动降级为普通模式。</p>
                  </div>
                  <button
                    onClick={() =>
                      updateSettings({ backgroundImageEnabled: !settings.backgroundImageEnabled })
                    }
                    className={`relative h-6 w-11 rounded-full transition-colors ${
                      (settings.backgroundImageEnabled || Boolean(settings.backgroundImageUrl) || Boolean(settings.backgroundImageBase64))
                        ? 'bg-[var(--od-accent)]'
                        : 'bg-[var(--od-border-strong)]'
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                        (settings.backgroundImageEnabled || Boolean(settings.backgroundImageUrl) || Boolean(settings.backgroundImageBase64))
                          ? 'translate-x-5'
                          : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>

                <div className="space-y-3">
                  <div className="od-fluid-panel rounded-lg p-3">
                    <p className="mb-2 text-sm font-medium text-[var(--od-text-secondary)]">内置背景图</p>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() =>
                          updateSettings({
                            backgroundImageEnabled: true,
                            backgroundImageUrl: defaultWinterBackground,
                            backgroundImageBase64: '',
                          })
                        }
                        className="rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-left text-xs text-[var(--od-text-primary)] transition-colors hover:border-[var(--od-accent)]"
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
                        className="rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-left text-xs text-[var(--od-text-primary)] transition-colors hover:border-[var(--od-accent)]"
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
                        className="rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-left text-xs text-[var(--od-text-primary)] transition-colors hover:border-[var(--od-accent)]"
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
                        className="rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-left text-xs text-[var(--od-text-primary)] transition-colors hover:border-[var(--od-accent)]"
                      >
                        Banner（内置）
                      </button>
                    </div>
                  </div>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">本地上传（Base64，最大 5MB）</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => handleUploadBackground(e.target.files?.[0] || null)}
                      className="w-full cursor-pointer rounded-lg border border-[var(--od-border)] bg-[var(--od-bg)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">背景图 URL</span>
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
                      className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    />
                  </label>

                  <div className="flex items-center justify-between gap-2 rounded-lg border border-[var(--od-border)] bg-[var(--od-bg)] px-3 py-2">
                    <span className="od-text-meta truncate">
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
                      className="rounded-md border border-[var(--od-border)] px-2.5 py-1 text-xs text-[var(--od-text-secondary)] transition-colors hover:text-[var(--od-text-primary)]"
                    >
                      清除背景图
                    </button>
                  </div>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--od-text-secondary)]">毛玻璃模式</span>
                    <select
                      value={settings.glassMode}
                      onChange={(e) =>
                        updateSettings({ glassMode: e.target.value as 'off' | 'on' | 'auto' })
                      }
                      className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg)] px-3 py-2 text-sm text-[var(--od-text-primary)]"
                    >
                      <option value="off">关闭</option>
                      <option value="on">开启</option>
                      <option value="auto">自动</option>
                    </select>
                  </label>

                  <label className="block">
                    <span className="mb-2 flex items-center justify-between text-sm font-medium text-[var(--od-text-secondary)]">
                      <span>背景图透明度</span>
                      <span className="od-text-code">{opacityDraft}%</span>
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
                      <span className="od-text-code">{blurDraft}px</span>
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
              <div className="flex items-center justify-between rounded-lg bg-[var(--od-bg-tertiary)] p-4">
                <div>
                  <p className="text-sm font-medium text-[var(--od-text-primary)]">紧凑模式</p>
                  <p className="text-xs text-[var(--od-text-tertiary)]">减少界面元素间距</p>
                </div>
                <button
                  onClick={() => updateSettings({ compactMode: !settings.compactMode })}
                  className={`relative h-6 w-11 rounded-full transition-colors ${settings.compactMode ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-border-strong)]'
                    }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${settings.compactMode ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                  />
                </button>
              </div>
            </div>
          </div>



          {/* 通知设置 */}
          <div className="od-fluid-panel rounded-xl p-6">
            <div className="mb-4 flex items-center gap-3">
              <Bell className="h-5 w-5 text-[var(--od-accent)]" />
              <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">通知</h2>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg bg-[var(--od-bg-tertiary)] p-4">
                <div>
                  <p className="text-sm font-medium text-[var(--od-text-primary)]">新帖通知</p>
                  <p className="text-xs text-[var(--od-text-tertiary)]">关注的频道有新帖时通知</p>
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
                  className={`relative h-6 w-11 rounded-full transition-colors ${settings.notifications.newPosts ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-border-strong)]'
                    }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${settings.notifications.newPosts ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between rounded-lg bg-[var(--od-bg-tertiary)] p-4">
                <div>
                  <p className="text-sm font-medium text-[var(--od-text-primary)]">回复通知</p>
                  <p className="text-xs text-[var(--od-text-tertiary)]">有人回复你的帖子时通知</p>
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
                  className={`relative h-6 w-11 rounded-full transition-colors ${settings.notifications.replies ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-border-strong)]'
                    }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${settings.notifications.replies ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between rounded-lg bg-[var(--od-bg-tertiary)] p-4">
                <div>
                  <p className="text-sm font-medium text-[var(--od-text-primary)]">提及通知</p>
                  <p className="text-xs text-[var(--od-text-tertiary)]">有人@你时通知</p>
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
                  className={`relative h-6 w-11 rounded-full transition-colors ${settings.notifications.mentions ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-border-strong)]'
                    }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${settings.notifications.mentions ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* 高级设置 */}
          <div className="od-fluid-panel rounded-xl p-6">
            <div className="mb-4 flex items-center gap-3">
              <SlidersHorizontal className="h-5 w-5 text-[var(--od-accent)]" />
              <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">高级</h2>
            </div>

            <button
              onClick={handleResetSettings}
              className="w-full rounded-lg bg-[var(--od-error)] p-3 text-left transition-colors hover:bg-[color-mix(in_oklab,var(--od-error)_85%,black)]"
            >
              <div className="text-sm font-medium text-white">重置设置</div>
              <div className="text-xs text-red-200">恢复所有设置到默认值</div>
            </button>
          </div>

          {/* 版本与更新 */}
          <div className="od-fluid-panel rounded-xl p-6">
            <div className="mb-3 flex items-center gap-3">
              <Info className="h-5 w-5 text-[var(--od-accent)]" />
              <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">版本与更新</h2>
            </div>
            <p className="text-sm text-[var(--od-text-secondary)]">
              当前前端版本：
              <span className="ml-1 font-mono text-[var(--od-text-primary)]">{APP_VERSION}</span>
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-[var(--od-text-tertiary)]">
              <li>新增帖子预览浮层与 Markdown 展示体验</li>
              <li>改进搜索筛选与列表/网格视图切换</li>
              <li>优化登出、Mock 环境与错误提示的健壮性</li>
            </ul>
          </div>

          {/* 提示信息 */}
          <div className="rounded-xl border border-[color-mix(in_oklab,var(--od-accent)_20%,transparent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)] p-4">
            <p className="text-sm text-[var(--od-text-secondary)]">
              💡 <span className="font-medium text-[var(--od-text-primary)]">提示：</span>
              设置保存在本地浏览器中，清除浏览器数据会重置设置。
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
