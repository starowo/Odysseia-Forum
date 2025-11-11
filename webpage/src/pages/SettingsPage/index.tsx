import { Settings, Moon, Sun, Monitor, Bell, Type, Layout, Grid, List } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { useSettings } from '@/hooks/useSettings';
import { resetUserSettings } from '@/lib/settings';
import { toast } from 'sonner';

export function SettingsPage() {
  const { settings, updateSettings } = useSettings();

  const handleResetSettings = () => {
    if (confirm('确定要重置所有设置为默认值吗？')) {
      resetUserSettings();
      toast.success('设置已重置为默认值');
      setTimeout(() => window.location.reload(), 1000);
    }
  };

  return (
    <MainLayout>
      <div>

        {/* 标题栏 */}
        <div className="border-b border-[#1e1f22] bg-[#2b2d31] px-4 py-4">
          <div className="flex items-center gap-3">
            <Settings className="h-6 w-6 text-[#f2f3f5]" />
            <div>
              <h1 className="text-xl font-bold text-[#f2f3f5]">设置</h1>
              <p className="text-sm text-[#b5bac1]">个性化你的体验</p>
            </div>
          </div>
        </div>

        {/* 设置内容 */}
        <div className="p-4 space-y-4">
          {/* 显示设置 */}
          <div className="rounded-xl bg-[#2b2d31] p-6">
            <div className="mb-4 flex items-center gap-3">
              <Layout className="h-5 w-5 text-[#5865f2]" />
              <h2 className="text-lg font-semibold text-[#f2f3f5]">显示设置</h2>
            </div>

            <div className="space-y-6">
              {/* 字体大小 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[#b5bac1]">
                  字体大小
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {(['small', 'medium', 'large'] as const).map((size) => (
                    <button
                      key={size}
                      onClick={() => updateSettings({ fontSize: size })}
                      className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${
                        settings.fontSize === size
                          ? 'border-[#5865f2] bg-[#5865f2]/10'
                          : 'border-[#3f4147] hover:border-[#5865f2]/50'
                      }`}
                    >
                      <Type className={`h-5 w-5 ${
                        settings.fontSize === size ? 'text-[#5865f2]' : 'text-[#b5bac1]'
                      }`} />
                      <span className={`text-sm ${
                        settings.fontSize === size ? 'text-[#5865f2] font-medium' : 'text-[#f2f3f5]'
                      }`}>
                        {size === 'small' ? '小' : size === 'medium' ? '中' : '大'}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 卡片大小 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[#b5bac1]">
                  卡片大小
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {(['compact', 'normal', 'large'] as const).map((size) => (
                    <button
                      key={size}
                      onClick={() => updateSettings({ cardSize: size })}
                      className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${
                        settings.cardSize === size
                          ? 'border-[#5865f2] bg-[#5865f2]/10'
                          : 'border-[#3f4147] hover:border-[#5865f2]/50'
                      }`}
                    >
                      <Layout className={`h-5 w-5 ${
                        settings.cardSize === size ? 'text-[#5865f2]' : 'text-[#b5bac1]'
                      }`} />
                      <span className={`text-sm ${
                        settings.cardSize === size ? 'text-[#5865f2] font-medium' : 'text-[#f2f3f5]'
                      }`}>
                        {size === 'compact' ? '紧凑' : size === 'normal' ? '标准' : '宽松'}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 布局模式 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[#b5bac1]">
                  布局模式
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => updateSettings({ layoutMode: 'grid' })}
                    className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-all ${
                      settings.layoutMode === 'grid'
                        ? 'border-[#5865f2] bg-[#5865f2]/10'
                        : 'border-[#3f4147] hover:border-[#5865f2]/50'
                    }`}
                  >
                    <Grid className={`h-5 w-5 ${
                      settings.layoutMode === 'grid' ? 'text-[#5865f2]' : 'text-[#b5bac1]'
                    }`} />
                    <div className="text-left">
                      <div className={`text-sm font-medium ${
                        settings.layoutMode === 'grid' ? 'text-[#5865f2]' : 'text-[#f2f3f5]'
                      }`}>
                        网格布局
                      </div>
                      <div className="text-xs text-[#949ba4]">卡片式显示</div>
                    </div>
                  </button>
                  <button
                    onClick={() => updateSettings({ layoutMode: 'list' })}
                    className={`flex items-center gap-3 rounded-lg border-2 p-4 transition-all ${
                      settings.layoutMode === 'list'
                        ? 'border-[#5865f2] bg-[#5865f2]/10'
                        : 'border-[#3f4147] hover:border-[#5865f2]/50'
                    }`}
                  >
                    <List className={`h-5 w-5 ${
                      settings.layoutMode === 'list' ? 'text-[#5865f2]' : 'text-[#b5bac1]'
                    }`} />
                    <div className="text-left">
                      <div className={`text-sm font-medium ${
                        settings.layoutMode === 'list' ? 'text-[#5865f2]' : 'text-[#f2f3f5]'
                      }`}>
                        列表布局
                      </div>
                      <div className="text-xs text-[#949ba4]">紧凑列表显示</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* 主题选择 */}
              <div>
                <label className="mb-3 block text-sm font-medium text-[#b5bac1]">主题</label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => updateSettings({ theme: 'light' })}
                    className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${
                      settings.theme === 'light'
                        ? 'border-[#5865f2] bg-[#5865f2]/10'
                        : 'border-[#3f4147] hover:border-[#5865f2]/50'
                    }`}
                  >
                    <Sun className="h-6 w-6 text-[#f2f3f5]" />
                    <span className="text-sm text-[#f2f3f5]">浅色</span>
                  </button>
                  <button
                    onClick={() => updateSettings({ theme: 'dark' })}
                    className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${
                      settings.theme === 'dark'
                        ? 'border-[#5865f2] bg-[#5865f2]/10'
                        : 'border-[#3f4147] hover:border-[#5865f2]/50'
                    }`}
                  >
                    <Moon className="h-6 w-6 text-[#f2f3f5]" />
                    <span className="text-sm text-[#f2f3f5]">深色</span>
                  </button>
                  <button
                    onClick={() => updateSettings({ theme: 'auto' })}
                    className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all ${
                      settings.theme === 'auto'
                        ? 'border-[#5865f2] bg-[#5865f2]/10'
                        : 'border-[#3f4147] hover:border-[#5865f2]/50'
                    }`}
                  >
                    <Monitor className="h-6 w-6 text-[#f2f3f5]" />
                    <span className="text-sm text-[#f2f3f5]">自动</span>
                  </button>
                </div>
              </div>

              {/* 紧凑模式 */}
              <div className="flex items-center justify-between rounded-lg bg-[#1e1f22] p-4">
                <div>
                  <p className="text-sm font-medium text-[#f2f3f5]">紧凑模式</p>
                  <p className="text-xs text-[#949ba4]">减少界面元素间距</p>
                </div>
                <button
                  onClick={() => updateSettings({ compactMode: !settings.compactMode })}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    settings.compactMode ? 'bg-[#5865f2]' : 'bg-[#4e5058]'
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
          <div className="rounded-xl bg-[#2b2d31] p-6">
            <div className="mb-4 flex items-center gap-3">
              <Bell className="h-5 w-5 text-[#5865f2]" />
              <h2 className="text-lg font-semibold text-[#f2f3f5]">通知</h2>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg bg-[#1e1f22] p-4">
                <div>
                  <p className="text-sm font-medium text-[#f2f3f5]">新帖通知</p>
                  <p className="text-xs text-[#949ba4]">关注的频道有新帖时通知</p>
                </div>
                <button
                  onClick={() => updateSettings({ 
                    notifications: { ...settings.notifications, newPosts: !settings.notifications.newPosts }
                  })}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    settings.notifications.newPosts ? 'bg-[#5865f2]' : 'bg-[#4e5058]'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                      settings.notifications.newPosts ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between rounded-lg bg-[#1e1f22] p-4">
                <div>
                  <p className="text-sm font-medium text-[#f2f3f5]">回复通知</p>
                  <p className="text-xs text-[#949ba4]">有人回复你的帖子时通知</p>
                </div>
                <button
                  onClick={() => updateSettings({ 
                    notifications: { ...settings.notifications, replies: !settings.notifications.replies }
                  })}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    settings.notifications.replies ? 'bg-[#5865f2]' : 'bg-[#4e5058]'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                      settings.notifications.replies ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between rounded-lg bg-[#1e1f22] p-4">
                <div>
                  <p className="text-sm font-medium text-[#f2f3f5]">提及通知</p>
                  <p className="text-xs text-[#949ba4]">有人@你时通知</p>
                </div>
                <button
                  onClick={() => updateSettings({ 
                    notifications: { ...settings.notifications, mentions: !settings.notifications.mentions }
                  })}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    settings.notifications.mentions ? 'bg-[#5865f2]' : 'bg-[#4e5058]'
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
          <div className="rounded-xl bg-[#2b2d31] p-6">
            <div className="mb-4 flex items-center gap-3">
              <Settings className="h-5 w-5 text-[#5865f2]" />
              <h2 className="text-lg font-semibold text-[#f2f3f5]">高级</h2>
            </div>

            <button 
              onClick={handleResetSettings}
              className="w-full rounded-lg bg-[#f23f42] p-3 text-left transition-colors hover:bg-[#da373c]"
            >
              <div className="text-sm font-medium text-white">重置设置</div>
              <div className="text-xs text-red-200">恢复所有设置到默认值</div>
            </button>
          </div>

          {/* 提示信息 */}
          <div className="rounded-xl bg-[#5865f2]/10 border border-[#5865f2]/20 p-4">
            <p className="text-sm text-[#b5bac1]">
              💡 <span className="font-medium text-[#f2f3f5]">提示：</span>
              设置保存在本地浏览器中，清除浏览器数据会重置设置。
            </p>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
