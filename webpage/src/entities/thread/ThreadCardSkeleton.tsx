export function ThreadCardSkeleton() {
  return (
    <article className="flex h-full w-full flex-col">
      <div className="flex flex-col gap-2 px-1 pb-3 pt-1 text-[var(--od-text-primary)]">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="h-6 w-6 animate-pulse rounded-full bg-[var(--od-bg-tertiary)] md:h-7 md:w-7" />
          <div className="min-w-0 flex-1">
            <div className="h-3.5 w-20 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
            <div className="mt-1 flex gap-2">
              <div className="h-2.5 w-14 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
              <div className="h-2.5 w-16 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
            </div>
          </div>
        </div>

        <div className="overflow-hidden">
          <div className="h-5 w-5/6 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
        </div>

      </div>

      <div className="aspect-[3/4] overflow-hidden rounded-[1.45rem] border border-[var(--od-shell-line)] bg-[var(--od-surface-shell)] shadow-[var(--od-shadow-soft)]">
        <div className="h-full w-full animate-shimmer bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-bg-secondary)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
      </div>

      <div className="flex flex-1 flex-col gap-3 px-1 pt-3">
        <div className="min-h-[2.75rem] space-y-2">
          <div className="h-3.5 w-full animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
          <div className="h-3.5 w-11/12 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
        </div>

        <div className="min-h-[2.75rem] content-start">
          <div className="flex flex-wrap gap-1.5">
          <div className="h-5 w-12 animate-shimmer rounded-md bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
          <div className="h-5 w-16 animate-shimmer rounded-md bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
          </div>
        </div>

        <div className="mt-auto flex items-center gap-2.5">
          <div className="h-3 w-8 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
          <div className="h-3 w-8 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
          <div className="h-3 w-8 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
        </div>

        <div className="h-px w-full bg-[linear-gradient(90deg,transparent,color-mix(in_srgb,var(--od-border-strong)_36%,transparent),transparent)]" />
      </div>
    </article>
  );
}
