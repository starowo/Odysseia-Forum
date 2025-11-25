import { useState, useEffect } from 'react';
import { X, Minimize2, Maximize2, ChevronLeft, ChevronRight } from 'lucide-react';
import { useSettings } from '@/hooks/useSettings';
import { LazyImage } from '@/components/common/LazyImage';
import { useSearchStore } from '@/features/search/store/searchStore';

export function FloatingBanner() {
    const { settings } = useSettings();
    const { isMainBannerVisible, activeBanner, bannerList, setActiveBanner, setPreviewThreadId } = useSearchStore();
    const [isMinimized, setIsMinimized] = useState(false);
    const [isVisible, setIsVisible] = useState(true);
    const [isHovered, setIsHovered] = useState(false);

    // Auto-rotation logic
    useEffect(() => {
        if (!activeBanner || bannerList.length <= 1 || isHovered || isMinimized || !isVisible) return;

        const timer = setInterval(() => {
            const currentIndex = bannerList.findIndex(b => b.id === activeBanner.id);
            const nextIndex = (currentIndex + 1) % bannerList.length;
            setActiveBanner(bannerList[nextIndex]);
        }, 5000);

        return () => clearInterval(timer);
    }, [activeBanner, bannerList, isHovered, isMinimized, isVisible, setActiveBanner]);

    const handlePrev = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (!activeBanner || bannerList.length <= 1) return;
        const currentIndex = bannerList.findIndex(b => b.id === activeBanner.id);
        const prevIndex = (currentIndex - 1 + bannerList.length) % bannerList.length;
        setActiveBanner(bannerList[prevIndex]);
    };

    const handleNext = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (!activeBanner || bannerList.length <= 1) return;
        const currentIndex = bannerList.findIndex(b => b.id === activeBanner.id);
        const nextIndex = (currentIndex + 1) % bannerList.length;
        setActiveBanner(bannerList[nextIndex]);
    };

    if (!settings.showFloatingBanner || !isVisible || isMainBannerVisible || !activeBanner) {
        return null;
    }

    const handleClose = () => {
        setIsVisible(false);
    };

    if (isMinimized) {
        return (
            <div className="fixed bottom-36 right-6 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
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
        <div
            className="fixed bottom-36 right-4 z-50 w-80 overflow-hidden rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] shadow-2xl animate-in fade-in slide-in-from-bottom-8 duration-500 group cursor-pointer"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            onClick={() => {
                if (activeBanner) {
                    setPreviewThreadId(activeBanner.id);
                }
            }}
        >
            {/* 顶部控制栏 */}
            <div className="absolute right-2 top-2 z-10 flex gap-2 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
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

            {/* 边缘导航按钮 - 仅 hover 显示，吸附边缘 */}
            {bannerList.length > 1 && (
                <>
                    <button
                        onClick={handlePrev}
                        className="absolute left-0 top-0 bottom-0 z-20 flex w-8 items-center justify-center bg-gradient-to-r from-black/40 to-transparent text-white opacity-0 transition-all duration-300 hover:w-10 hover:from-black/60 group-hover:opacity-100"
                        aria-label="上一张"
                    >
                        <ChevronLeft className="h-5 w-5 drop-shadow-md" />
                    </button>
                    <button
                        onClick={handleNext}
                        className="absolute right-0 top-0 bottom-0 z-20 flex w-8 items-center justify-center bg-gradient-to-l from-black/40 to-transparent text-white opacity-0 transition-all duration-300 hover:w-10 hover:from-black/60 group-hover:opacity-100"
                        aria-label="下一张"
                    >
                        <ChevronRight className="h-5 w-5 drop-shadow-md" />
                    </button>
                </>
            )}

            {/* 图片区域 */}
            <div className="relative h-40 w-full">
                <LazyImage
                    src={activeBanner.image}
                    alt={activeBanner.title}
                    className="h-full w-full object-cover transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent pointer-events-none" />

                <div className="absolute bottom-3 left-4 right-4 pointer-events-none">
                    <h3 className="text-lg font-bold text-white text-shadow-sm line-clamp-1">
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
