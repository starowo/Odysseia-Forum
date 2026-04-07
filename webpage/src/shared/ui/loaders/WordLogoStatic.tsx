import { cn } from '@/shared/lib/utils';

interface WordLogoStaticProps {
  className?: string; // 控制容器外部样式，如 height (决定整个字体大小)
}

export function WordLogoStatic({ className }: WordLogoStaticProps) {
  // 通用路径线条属性
  const pathConfig = {
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '11',
    strokeLinejoin: 'round' as const,
    strokeLinecap: 'round' as const,
  };

  // 通过 h-full 和 aspect-square 确保宽高比一致，并跟随外部容器的高度缩放
  const svgClass = 'h-full aspect-square overflow-visible';

  return (
    <div className={cn('flex flex-nowrap items-center gap-[1px]', className)}>
      {/* O (Omicron) - Static with Gap & Dot at 12 o'clock */}
      <svg viewBox="0 0 80 80" className={svgClass}>
        {/* 将 9点钟作为起始点的路径旋转90度，让缺口朝上 (12点方向) */}
        <g transform="rotate(90 40 40)">
          <path 
            d="M 16 40 A 24 24 0 1 0 16 39.99 Z" 
            {...pathConfig} 
            strokeDasharray="113 38"
            strokeDashoffset="132"
          />
        </g>
        {/* 在正12点的断口处补充能量圆点 */}
        <circle cx="40" cy="16" r="6" className="fill-[var(--od-accent)]" />
      </svg>

      {/* Δ (Delta) */}
      <svg viewBox="0 0 80 80" className={svgClass}>
        <path d="M 40 16 L 64 64 L 16 64 Z" {...pathConfig} />
      </svg>

      {/* Υ (Upsilon) */}
      <svg viewBox="0 0 80 80" className={svgClass}>
        <path d="M 16 16 L 40 40 L 40 64 M 40 40 L 64 16" {...pathConfig} />
      </svg>

      {/* Σ (Sigma) */}
      <svg viewBox="0 0 80 80" className={svgClass}>
        <path d="M 60 16 L 24 16 L 44 40 L 24 64 L 60 64" {...pathConfig} />
      </svg>

      {/* Σ (Sigma) */}
      <svg viewBox="0 0 80 80" className={svgClass}>
        <path d="M 60 16 L 24 16 L 44 40 L 24 64 L 60 64" {...pathConfig} />
      </svg>

      {/* Ε (Epsilon) */}
      <svg viewBox="0 0 80 80" className={svgClass}>
        <path d="M 60 16 L 24 16 L 24 64 L 60 64 M 24 40 L 52 40" {...pathConfig} />
      </svg>

      {/* Ι (Iota) */}
      <svg viewBox="0 0 80 80" className={svgClass}>
        <path d="M 40 16 L 40 64" {...pathConfig} />
      </svg>

      {/* Α (Alpha) */}
      <svg viewBox="0 0 80 80" className={svgClass}>
        <path d="M 16 64 L 40 16 L 64 64 M 26 44 L 54 44" {...pathConfig} />
      </svg>
    </div>
  );
}
