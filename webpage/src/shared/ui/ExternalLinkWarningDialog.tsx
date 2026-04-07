interface ExternalLinkWarningDialogProps {
  hostname: string;
  href: string;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ExternalLinkWarningDialog({
  hostname,
  href,
  onCancel,
  onConfirm,
}: ExternalLinkWarningDialogProps) {
  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="external-link-warning-title"
      onClick={onCancel}
    >
      <div
        className="od-floating-panel-solid w-full max-w-lg rounded-2xl border border-[var(--od-border)] p-6 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-[var(--od-text-tertiary)]">
          外部链接提醒
        </p>
        <h2 id="external-link-warning-title" className="text-xl font-semibold text-[var(--od-text-primary)]">
          即将离开 Odysseia / Discord 生态
        </h2>
        <p className="mt-3 text-sm leading-6 text-[var(--od-text-secondary)]">
          这个链接指向站外页面。请确认目标站点可信后再继续访问。
        </p>
        <div className="mt-4 rounded-xl border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-4 py-3">
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--od-text-tertiary)]">目标域名</p>
          <p className="mt-1 break-all text-sm font-medium text-[var(--od-text-primary)]">{hostname}</p>
          <p className="mt-2 break-all text-xs text-[var(--od-text-tertiary)]">{href}</p>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg px-4 py-2 text-sm font-medium text-[var(--od-text-secondary)] transition-colors hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--od-accent-hover)]"
          >
            继续前往
          </button>
        </div>
      </div>
    </div>
  );
}
