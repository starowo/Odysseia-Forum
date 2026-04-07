const TRUSTED_DISCORD_HOSTS = [
  'discord.com',
  'discord.gg',
  'discordapp.com',
  'discordapp.net',
];

const TRUSTED_DISCORD_EXACT_HOSTS = new Set([
  'www.discord.com',
  'cdn.discordapp.com',
  'media.discordapp.net',
]);

export interface UrlSafetyInfo {
  href: string;
  hostname: string;
  isTrustedDiscord: boolean;
  requiresExternalWarning: boolean;
}

export function parseHttpUrl(rawUrl: string): URL | null {
  const trimmed = rawUrl.trim();
  if (!trimmed) return null;

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function isTrustedDiscordHostname(hostname: string): boolean {
  const normalized = hostname.trim().toLowerCase();
  if (!normalized) return false;

  if (TRUSTED_DISCORD_EXACT_HOSTS.has(normalized)) {
    return true;
  }

  return TRUSTED_DISCORD_HOSTS.some((host) => normalized === host || normalized.endsWith(`.${host}`));
}

export function getUrlSafetyInfo(rawUrl: string): UrlSafetyInfo | null {
  const parsed = parseHttpUrl(rawUrl);
  if (!parsed) return null;

  const hostname = parsed.hostname.toLowerCase();
  const isTrustedDiscord = isTrustedDiscordHostname(hostname);

  return {
    href: parsed.toString(),
    hostname,
    isTrustedDiscord,
    requiresExternalWarning: !isTrustedDiscord,
  };
}
