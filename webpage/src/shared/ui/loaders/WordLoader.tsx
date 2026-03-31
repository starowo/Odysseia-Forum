import { cn } from '@/shared/lib/utils';
import { OmicronLoader } from './OmicronLoader';

interface WordLoaderProps {
  className?: string; // 控制容器外部样式，如 padding, margin
}

export function WordLoader({ className }: WordLoaderProps) {
  // 通用路径线条属性，保持圆润连贯
  const pathConfig = {
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '10',
    strokeLinejoin: 'round' as const,
    strokeLinecap: 'round' as const,
  };

  const letterClass = 'w-11 h-11 relative inline-block text-[var(--od-text-primary)]';
  const svgClass = 'block w-full h-full overflow-visible';

  return (
    <div className={cn('flex flex-wrap items-center justify-center gap-5', className)}>
      {/* O (Omicron) - Animated */}
      <OmicronLoader className="w-11 h-11" />

      {/* Δ (Delta) */}
      <div className={letterClass}>
        <svg viewBox="0 0 80 80" className={svgClass}>
          <path d="M 40 16 L 64 64 L 16 64 Z" {...pathConfig} />
        </svg>
      </div>

      {/* Υ (Upsilon) */}
      <div className={letterClass}>
        <svg viewBox="0 0 80 80" className={svgClass}>
          <path d="M 16 16 L 40 40 L 40 64 M 40 40 L 64 16" {...pathConfig} />
        </svg>
      </div>

      {/* Σ (Sigma) */}
      <div className={letterClass}>
        <svg viewBox="0 0 80 80" className={svgClass}>
          <path d="M 60 16 L 24 16 L 44 40 L 24 64 L 60 64" {...pathConfig} />
        </svg>
      </div>

      {/* Σ (Sigma) */}
      <div className={letterClass}>
        <svg viewBox="0 0 80 80" className={svgClass}>
          <path d="M 60 16 L 24 16 L 44 40 L 24 64 L 60 64" {...pathConfig} />
        </svg>
      </div>

      {/* Ε (Epsilon) */}
      <div className={letterClass}>
        <svg viewBox="0 0 80 80" className={svgClass}>
          <path d="M 60 16 L 24 16 L 24 64 L 60 64 M 24 40 L 52 40" {...pathConfig} />
        </svg>
      </div>

      {/* Ι (Iota) */}
      <div className={letterClass}>
        <svg viewBox="0 0 80 80" className={svgClass}>
          <path d="M 40 16 L 40 64" {...pathConfig} />
        </svg>
      </div>

      {/* Α (Alpha) */}
      <div className={letterClass}>
        <svg viewBox="0 0 80 80" className={svgClass}>
          <path d="M 16 64 L 40 16 L 64 64 M 26 44 L 54 44" {...pathConfig} />
        </svg>
      </div>
    </div>
  );
}
