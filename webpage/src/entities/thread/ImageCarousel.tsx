import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

interface ImageCarouselProps {
  images: string[];
  alt?: string;
  className?: string;
  autoPlayInterval?: number;
}

export function ImageCarousel({
  images,
  alt = 'Image carousel',
  className = '',
  autoPlayInterval = 4000,
}: ImageCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [direction, setDirection] = useState<1 | -1>(1);

  const goToNext = useCallback(() => {
    setDirection(1);
    setCurrentIndex((prev) => (prev + 1) % images.length);
  }, [images.length]);

  const goToPrev = useCallback(() => {
    setDirection(-1);
    setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
  }, [images.length]);

  const goToIndex = (idx: number) => {
    setDirection(idx > currentIndex ? 1 : -1);
    setCurrentIndex(idx);
  };

  // 自动轮播逻辑
  useEffect(() => {
    if (images.length <= 1 || isHovered) return;

    const timer = setInterval(goToNext, autoPlayInterval);
    return () => clearInterval(timer);
  }, [images.length, isHovered, autoPlayInterval, goToNext]);

  // 如果没有图片
  if (!images || images.length === 0) return null;

  // 单图模式，直接显示，不需要多余的按键和轮播
  if (images.length === 1) {
    return (
      <div className={`relative w-full overflow-hidden ${className}`}>
        <img
          src={images[0]}
          alt={alt}
          className="h-full w-full object-cover"
        />
      </div>
    );
  }

  // 多图轮播模式
  const variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? '100%' : '-100%',
      opacity: 0,
    }),
    center: {
      zIndex: 1,
      x: 0,
      opacity: 1,
    },
    exit: (direction: number) => ({
      zIndex: 0,
      x: direction < 0 ? '100%' : '-100%',
      opacity: 0,
    }),
  };

  return (
    <div
      className={`group relative flex w-full overflow-hidden bg-[var(--od-bg-tertiary)] ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 轮播图片层 */}
      <AnimatePresence initial={false} custom={direction}>
        <motion.img
          key={currentIndex}
          src={images[currentIndex]}
          custom={direction}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{
            x: { type: 'spring', stiffness: 300, damping: 30 },
            opacity: { duration: 0.2 },
          }}
          alt={`${alt} - ${currentIndex + 1}`}
          className="absolute inset-0 h-full w-full object-cover"
        />
      </AnimatePresence>

      {/* 左侧点击区（隐藏的导航按钮） */}
      <div
        className="absolute bottom-0 left-0 top-0 z-10 w-1/3 cursor-pointer"
        onClick={goToPrev}
      />
      {/* 右侧点击区 */}
      <div
        className="absolute bottom-0 right-0 top-0 z-10 w-1/3 cursor-pointer"
        onClick={goToNext}
      />

      {/* 显式左右箭头指示器（仅在 Hover 时有少许透明度提示） */}
      <div className="absolute inset-y-0 left-2 z-20 flex items-center pointer-events-none opacity-0 transition-opacity duration-300 group-hover:opacity-100">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur-md">
          <ChevronLeft className="h-5 w-5" />
        </div>
      </div>
      <div className="absolute inset-y-0 right-2 z-20 flex items-center pointer-events-none opacity-0 transition-opacity duration-300 group-hover:opacity-100">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur-md">
          <ChevronRight className="h-5 w-5" />
        </div>
      </div>

      {/* 底部小圆点 */}
      <div className="absolute bottom-3 left-0 right-0 z-20 flex justify-center gap-2">
        {images.map((_, idx) => (
          <button
            key={idx}
            onClick={(e) => {
              e.stopPropagation();
              goToIndex(idx);
            }}
            className={`h-2 rounded-full transition-all duration-300 ${
              idx === currentIndex
                ? 'w-6 bg-[var(--od-accent)]'
                : 'w-2 bg-white/50 hover:bg-white/80'
            }`}
            aria-label={`Go to slide ${idx + 1}`}
          />
        ))}
      </div>
    </div>
  );
}
