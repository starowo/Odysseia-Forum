import { cn } from '@/shared/lib/utils';

interface OmicronLoaderProps {
  className?: string; // 控制整个 SVG 外壳大小
}

export function OmicronLoader({ className }: OmicronLoaderProps) {
  return (
    <div className={cn('relative inline-block w-8 h-8', className)}>
      <svg viewBox="0 0 80 80" className="block w-full h-full overflow-visible">
        {/* Animated Path */}
        <path
          d="M 16 40 A 24 24 0 1 0 16 39.99 Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeLinejoin="round"
          strokeLinecap="round"
          className="omicron-loader-path text-[var(--od-text-primary)]"
        />
        {/* Orbiting Dot */}
        <circle
          cx="0"
          cy="0"
          r="6"
          className="omicron-loader-dot fill-[var(--od-accent)]"
        />
      </svg>
    </div>
  );
}
