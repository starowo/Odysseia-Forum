export const LOGIN_REDIRECT_STORAGE_KEY = 'login_redirect';

export function buildCurrentAppRedirect(): string {
  if (typeof window === 'undefined') return '/';
  const { pathname, search, hash } = window.location;
  return sanitizeInternalRedirect(`${pathname}${search}${hash}`);
}

export function sanitizeInternalRedirect(target: string | null | undefined): string {
  if (!target) return '/';

  const trimmed = target.trim();
  if (!trimmed || !trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.includes('\\')) {
    return '/';
  }

  try {
    const baseOrigin = typeof window !== 'undefined' ? window.location.origin : 'https://odysseia.local';
    const parsed = new URL(trimmed, baseOrigin);
    if (parsed.origin !== baseOrigin || !parsed.pathname.startsWith('/')) {
      return '/';
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return '/';
  }
}
