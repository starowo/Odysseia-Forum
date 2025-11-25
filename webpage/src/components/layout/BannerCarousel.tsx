import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Plus, Image as ImageIcon } from 'lucide-react';
import { BannerApplicationModal } from '@/features/banner/components/BannerApplicationModal';

interface Banner {
  id: string;
  image: string;
  title: string;
  description: string;
  link?: string;
}

interface BannerCarouselProps {
  banners: Banner[];
  autoPlayInterval?: number;
}

export function BannerCarousel({ banners, autoPlayInterval = 5000 }: BannerCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);

  useEffect(() => {
    if (isHovered || banners.length <= 1) return;

    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % banners.length);
    }, autoPlayInterval);

    return () => clearInterval(timer);
  }, [isHovered, banners.length, autoPlayInterval]);

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev - 1 + banners.length) % banners.length);
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev + 1) % banners.length);
  };

  if (banners.length === 0) {
    return (
      <div className="mb-4 overflow-hidden rounded-xl bg-[#2b2d31]">
        <div className="flex aspect-[21/9] items-center justify-center">
          <div className="text-center">
            <div className="mb-2 text-4xl">🎉</div>
            <p className="text-lg font-semibold text-[#f2f3f5]">
              欢迎使用 Odysseia 论坛搜索
            </p>
          </div>
        </div>
      </div>
    );
  }

  const currentBanner = banners[currentIndex];

  return (
    <div
      className="group relative mb-4 overflow-hidden rounded-xl bg-[#2b2d31]"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Banner 图片 */}
      <div className="relative aspect-[21/9]">
        <img
          src={currentBanner.image}
          alt={currentBanner.title}
          className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
        />

        {/* 渐变遮罩 */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent" />

        {/* 内容 */}
        <div className="absolute bottom-0 left-0 right-0 p-6">
          <h2 className="mb-2 text-2xl font-bold text-white">
            {currentBanner.title}
          </h2>
          <p className="text-sm text-gray-200">
            {currentBanner.description}
          </p>
        </div>
      </div>

      {/* 导航按钮 */}
      {banners.length > 1 && (
        <>
          <button
            onClick={goToPrevious}
            className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white opacity-0 transition-opacity hover:bg-black/70 group-hover:opacity-100"
            aria-label="上一张"
          >
            <ChevronLeft className="h-6 w-6" />
          </button>
          <button
            onClick={goToNext}
            className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white opacity-0 transition-opacity hover:bg-black/70 group-hover:opacity-100"
            aria-label="下一张"
          >
            <ChevronRight className="h-6 w-6" />
          </button>
        </>
      )}

      {/* 指示器 */}
      {banners.length > 1 && (
        <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
          {banners.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentIndex(index)}
              className={`h-2 rounded-full transition-all ${index === currentIndex
                ? 'w-8 bg-white'
                : 'w-2 bg-white/50 hover:bg-white/75'
                }`}
              aria-label={`跳转到第 ${index + 1} 张`}
            />
          ))}
        </div>
      )}

      {/* Banner 申请入口 - 左上角半透明下拉 */}
      <div className="absolute top-0 left-0 p-4 z-10">
        <div className="group/apply relative">
          {/* 触发区域 */}
          <button
            className="flex items-center justify-center w-8 h-8 rounded-full bg-black/20 text-white/50 backdrop-blur-[2px] transition-all duration-300 hover:bg-black/40 hover:text-white"
            aria-label="Banner 选项"
          >
            <Plus className="w-5 h-5" />
          </button>

          {/* 下拉菜单 */}
          <div className="absolute top-full left-0 mt-2 w-32 origin-top-left scale-95 opacity-0 invisible transition-all duration-200 group-hover/apply:scale-100 group-hover/apply:opacity-100 group-hover/apply:visible">
            <button
              onClick={() => setIsApplyModalOpen(true)}
              className="flex w-full items-center gap-2 rounded-lg bg-black/60 px-3 py-2 text-sm font-medium text-white backdrop-blur-md hover:bg-[var(--od-accent)] transition-colors shadow-lg"
            >
              <ImageIcon className="w-4 h-4" />
              申请 Banner
            </button>
          </div>
        </div>
      </div>

      <BannerApplicationModal
        isOpen={isApplyModalOpen}
        onClose={() => setIsApplyModalOpen(false)}
      />
    </div>
  );
}
