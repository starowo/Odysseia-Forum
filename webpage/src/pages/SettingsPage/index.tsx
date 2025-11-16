import { Settings, Moon, Sun, Monitor, Bell, Type, Layout, Grid, List } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { useSettings } from '@/hooks/useSettings';
import { resetUserSettings } from '@/lib/settings';
import { toast } from 'sonner';
import { themes } from '@/styles/themes';

export function SettingsPage() {
  const { settings, updateSettings } = useSettings();

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
      id: 'tweak-gray-dark' as const,
      label: '灰调深色',
      icon: Moon,
      themeKey: 'tweakGrayDark' as const,
      description: 'Tweak 灰调暗色配色',
    },
    {
      id: 'tweak-gray-light' as const,
      label: '灰调浅色',
      icon: Sun,
      themeKey: 'tweakGrayLight' as const,
      description: 'Tweak 灰调浅色配色',
    },
    {
      id: 'paper-dark' as const,
      label: '纸感深色',
      icon: Moon,
      themeKey: 'paperDark' as const,
      description: '偏暖的纸感深色主题',
    },
    {
      id: 'paper-light' as const,
      label: '纸感浅色',
      icon: Sun,
      themeKey: 'paperLight' as const,
      description: '淡黄色纸张风格浅色主题',
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
    <MainLayout>
      <div className="bg-[var(--od-bg)] text-[var(--od-text-primary)]">
        {/* 标题栏 */}
        <div className="border-b border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-4 py-4">
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
          <div className="rounded-xl bg-[var(--od-card)] p-6">
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
                  {(['small', 'medium', 'large'] as const).map((size) => (
                    <button
                      key={size}
                      onClick={() => updateSettings({ fontSize: size })}
                      className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${
                        settings.fontSize === size
                          ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                          : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                      }`}
                    >
                      <Type
                        className={`h-5 w-5 ${
                          settings.fontSize === size
                            ? 'text-[var(--od-accent)]'
                            : 'text-[var(--od-text-secondary)]'
                        }`}
                      />
                      <span
                        className={`text-sm ${
                          settings.fontSize === size
                            ? 'text-[var(--od-text-primary)] font-medium'
                            : 'text-[var(--od-text-primary)]'
                        }`}
                      >
                        {size === 'small' ? '小' : size === 'medium' ? '中' : '大'}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 卡片大小 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[var(--od-text-secondary)]">
                  卡片大小
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {(['compact', 'normal', 'large'] as const).map((size) => (
                    <button
                      key={size}
                      onClick={() => updateSettings({ cardSize: size })}
                      className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${
                        settings.cardSize === size
                          ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                          : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                      }`}
                    >
                      <Layout
                        className={`h-5 w-5 ${
                          settings.cardSize === size
                            ? 'text-[var(--od-accent)]'
                            : 'text-[var(--od-text-secondary)]'
                        }`}
                      />
                      <span
                        className={`text-sm ${
                          settings.cardSize === size
                            ? 'text-[var(--od-text-primary)] font-medium'
                            : 'text-[var(--od-text-primary)]'
                        }`}
                      >
                        {size === 'compact' ? '紧凑' : size === 'normal' ? '标准' : '宽松'}
                      </span>
                    </button>
                  ))}
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
                    className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-all ${
                      settings.layoutMode === 'grid'
                        ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                        : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                    }`}
                  >
                    <Grid
                      className={`h-5 w-5 ${
                        settings.layoutMode === 'grid'
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
                    className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-all ${
                      settings.layoutMode === 'list'
                        ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                        : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                    }`}
                  >
                    <List
                      className={`h-5 w-5 ${
                        settings.layoutMode === 'list'
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
                        className={`flex flex-col gap-2 rounded-lg border-2 p-3 text-left transition-all ${
                          isSelected
                            ? 'border-[var(--od-accent)] bg-[color-mix(in_oklab,var(--od-accent)_10%,transparent)]'
                            : 'border-[var(--od-border-strong)] hover:border-[var(--od-accent)]/60'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <option.icon
                              className={`h-5 w-5 ${
                                isSelected
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

              {/* 紧凑模式 */}
              <div className="flex items-center justify-between rounded-lg bg-[var(--od-bg-tertiary)] p-4">
                <div>
                  <p className="text-sm font-medium text-[var(--od-text-primary)]">紧凑模式</p>
                  <p className="text-xs text-[var(--od-text-tertiary)]">减少界面元素间距</p>
                </div>
                <button
                  onClick={() => updateSettings({ compactMode: !settings.compactMode })}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    settings.compactMode ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-border-strong)]'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                      settings.compactMode ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* 通知设置 */}
          <div className="rounded-xl bg-[var(--od-card)] p-6">
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
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    settings.notifications.newPosts ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-border-strong)]'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                      settings.notifications.newPosts ? 'translate-x-5' : 'translate-x-0.5'
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
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    settings.notifications.replies ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-border-strong)]'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                      settings.notifications.replies ? 'translate-x-5' : 'translate-x-0.5'
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
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    settings.notifications.mentions ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-border-strong)]'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                      settings.notifications.mentions ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* 高级设置 */}
          <div className="rounded-xl bg-[var(--od-card)] p-6">
            <div className="mb-4 flex items-center gap-3">
              <Settings className="h-5 w-5 text-[var(--od-accent)]" />
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
          <div className="rounded-xl bg-[var(--od-card)] p-6">
            <div className="mb-3 flex items-center gap-3">
              <Settings className="h-5 w-5 text-[var(--od-accent)]" />
              <h2 className="text-lg font-semibold text-[var(--od-text-primary)]">版本与更新</h2>
            </div>
            <p className="text-sm text-[var(--od-text-secondary)]">
              当前前端版本：
              <span className="ml-1 font-mono text-[var(--od-text-primary)]">2.0.0</span>
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
    </MainLayout>
  );
}
