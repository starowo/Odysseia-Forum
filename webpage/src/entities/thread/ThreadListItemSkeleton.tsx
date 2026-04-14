export function ThreadListItemSkeleton() {
  return (
    <article className="relative w-full py-3">
      <div className="absolute inset-x-0 bottom-0 h-px bg-[linear-gradient(90deg,transparent,color-mix(in_srgb,var(--od-divider-strong)_50%,transparent),transparent)]" />

      <div className="flex flex-col gap-4 md:flex-row md:items-start md:gap-5">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center gap-2">
            <div className="h-6 w-6 animate-pulse rounded-full bg-[var(--od-bg-tertiary)] md:h-7 md:w-7" />
            <div className="h-3 w-20 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
            <div className="h-3 w-12 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
            <div className="h-3 w-16 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
          </div>

          <div className="mb-3 space-y-2">
            <div className="h-5 w-4/5 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
            <div className="h-5 w-3/5 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
          </div>

          <div className="mb-3 space-y-2">
            <div className="h-3.5 w-full animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
            <div className="h-3.5 w-11/12 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <div className="flex flex-wrap gap-2">
              <div className="h-3 w-10 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
              <div className="h-3 w-12 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
              <div className="h-3 w-8 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
            </div>
            <div className="flex items-center gap-3 md:ml-4">
              <div className="h-3 w-8 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
              <div className="h-3 w-8 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
              <div className="h-3 w-8 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
            </div>
          </div>
        </div>

        <div className="grid shrink-0 grid-cols-2 gap-2 md:w-[10.5rem] md:grid-cols-3">
          <div className="h-24 animate-shimmer overflow-hidden rounded-[1rem] bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%] md:h-24" />
          <div className="h-20 animate-shimmer overflow-hidden rounded-[1rem] bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%] md:h-24" />
          <div className="hidden h-20 animate-shimmer overflow-hidden rounded-[1rem] bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%] md:block md:h-24" />
        </div>
      </div>
    </article>
  );
}
