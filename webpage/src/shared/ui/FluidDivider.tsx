import type { CSSProperties } from 'react';
import { cn } from '@/shared/lib/utils';

interface FluidDividerProps {
  className?: string;
  label?: string;
  align?: 'left' | 'center' | 'right';
  tone?: 'default' | 'strong';
}

export function FluidDivider({
  className,
  label,
  align = 'left',
  tone = 'default',
}: FluidDividerProps) {
  const lineTone = tone === 'strong' ? 'var(--od-divider-strong)' : 'var(--od-divider)';
  const justifyClass =
    align === 'center' ? 'justify-center text-center' : align === 'right' ? 'justify-end text-right' : 'justify-start text-left';

  return (
    <div className={cn('od-fluid-divider-wrap', justifyClass, className)} aria-hidden="true">
      <div className="od-fluid-divider-line" style={{ '--od-divider-line-color': lineTone } as CSSProperties} />
      {label ? <span className="od-fluid-divider-label">{label}</span> : null}
    </div>
  );
}
