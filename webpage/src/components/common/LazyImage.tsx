import { useState, useEffect, useRef } from 'react';
import { useSettings } from '@/hooks/useSettings';

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  placeholder?: string;
}

export function LazyImage({ src, alt, className = '', placeholder }: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLDivElement>(null);
  const { settings } = useSettings();
  const isImageDisabled = settings.imageMode === 'off';

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        rootMargin: '50px',
      }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={imgRef} className={`relative ${className}`}>
      {isImageDisabled ? (
        // 节省流量模式：不请求实际图片，只显示轻量占位
        <div className="absolute inset-0 flex items-center justify-center bg-[color-mix(in_oklab,var(--od-bg-tertiary)_85%,transparent)]">
          <div className="flex flex-col items-center gap-1">
            <div className="h-8 w-8 rounded-md border border-[var(--od-border-strong)] bg-[color-mix(in_oklab,var(--od-bg-secondary)_85%,transparent)]" />
            <span className="text-[10px] text-[var(--od-text-tertiary)]">图片已关闭（设置中可开启）</span>
          </div>
        </div>
      ) : (
        <>
          {/* 占位符/加载动画 */}
          {!isLoaded && (
            <div className="absolute inset-0 flex items-center justify-center bg-[color-mix(in_oklab,var(--od-bg-tertiary)_85%,transparent)]">
              {placeholder ? (
                <img src={placeholder} alt="" className="h-full w-full object-cover opacity-50" />
              ) : (
                <div className="flex flex-col items-center gap-2">
                  {/* Spinner removed as per user request */}
                </div>
              )}
            </div>
          )}

          {/* 实际图片 */}
          {isInView && (
            <img
              src={src}
              alt={alt}
              className={`h-full w-full object-cover transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'
                }`}
              onLoad={() => setIsLoaded(true)}
              loading="lazy"
            />
          )}
        </>
      )}
    </div>
  );
}
