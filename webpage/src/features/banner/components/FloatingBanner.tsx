import { useState } from 'react';
import { X, Minimize2, Maximize2 } from 'lucide-react';
import { useSettings } from '@/hooks/useSettings';
import { LazyImage } from '@/components/common/LazyImage';
import { useSearchStore } from '@/features/search/store/searchStore';

export function FloatingBanner() {
    const { settings } = useSettings();
    const { isMainBannerVisible, activeBanner } = useSearchStore();
    const [isMinimized, setIsMinimized] = useState(false);
    const [isVisible, setIsVisible] = useState(true);

    // console.log('[FloatingBanner] State:', {
    //     showSetting: settings.showFloatingBanner,
    //     userVisible: isVisible,
    //     mainBannerVisible: isMainBannerVisible,
    //     hasActiveBanner: !!activeBanner
    // });

    // 只有当：
    // 1. 设置开启
    // 2. 用户未手动关闭 (isVisible)
    // 3. 主 Banner 不可见 (isMainBannerVisible === false)
    // 4. 有有效的 Banner 数据
    // 才显示
    if (!settings.showFloatingBanner || !isVisible || isMainBannerVisible || !activeBanner) {
        return null;
    }

    const handleClose = () => {
        setIsVisible(false);
        // 可选：如果用户点击关闭，是否意味着永久关闭？
        // 这里暂时只做本次会话关闭，或者可以更新设置
        // updateSettings({ showFloatingBanner: false });
    };

    if (isMinimized) {
        return (
            <div className="fixed bottom-20 right-6 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
                <button
                    onClick={() => setIsMinimized(false)}
                    className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--od-accent)] text-white shadow-lg transition-transform hover:scale-110 hover:bg-[var(--od-accent-hover)]"
                    title="展开欢迎横幅"
                >
                    <Maximize2 className="h-6 w-6" />
                </button>
            </div>
        );
    }

    return (
        <div className="fixed bottom-20 right-4 z-50 w-80 overflow-hidden rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] shadow-2xl animate-in fade-in slide-in-from-bottom-8 duration-500">
            {/* 顶部控制栏 */}
            <div className="absolute right-2 top-2 z-10 flex gap-2">
                <button
                    onClick={() => setIsMinimized(true)}
                    className="rounded-full bg-black/40 p-1 text-white backdrop-blur-sm transition-colors hover:bg-black/60"
                    title="最小化"
                >
                    <Minimize2 className="h-3.5 w-3.5" />
                </button>
                <button
                    onClick={handleClose}
                    className="rounded-full bg-black/40 p-1 text-white backdrop-blur-sm transition-colors hover:bg-black/60"
                    title="关闭"
                >
                    <X className="h-3.5 w-3.5" />
                </button>
            </div>

            {/* 图片区域 */}
            <div className="relative h-40 w-full">
                <LazyImage
                    src={activeBanner.image}
                    alt={activeBanner.title}
                    className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />

                <div className="absolute bottom-3 left-4 right-4">
                    <h3 className="text-lg font-bold text-white text-shadow-sm">
                        {activeBanner.title}
                    </h3>
                    <p className="text-xs text-gray-200 line-clamp-1">
                        {activeBanner.description}
                    </p>
                </div>
            </div>
        </div>
    );
}
