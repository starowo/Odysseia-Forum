import { cn } from '@/shared/lib/utils';

type SettingsToggleProps = {
  checked: boolean;
  onToggle: () => void;
  className?: string;
  ariaLabel: string;
};

export function SettingsToggle({ checked, onToggle, className, ariaLabel }: SettingsToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      onClick={onToggle}
      data-checked={checked ? 'true' : 'false'}
      className={cn('od-toggle', className)}
    >
      <span className="od-toggle-thumb" />
    </button>
  );
}
