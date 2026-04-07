import { describe, expect, it } from 'vitest';
import { getUrlSafetyInfo, isTrustedDiscordHostname, parseHttpUrl } from './urlSafety';

describe('urlSafety', () => {
  it('只接受 http/https 链接', () => {
    expect(parseHttpUrl('https://discord.com/channels/1/2/3')?.hostname).toBe('discord.com');
    expect(parseHttpUrl('javascript:alert(1)')).toBeNull();
    expect(parseHttpUrl('data:text/html,test')).toBeNull();
  });

  it('正确识别 Discord 可信域名', () => {
    expect(isTrustedDiscordHostname('discord.com')).toBe(true);
    expect(isTrustedDiscordHostname('media.discordapp.net')).toBe(true);
    expect(isTrustedDiscordHostname('sub.discord.gg')).toBe(true);
    expect(isTrustedDiscordHostname('example.com')).toBe(false);
  });

  it('对非 Discord 外链标记警告', () => {
    expect(getUrlSafetyInfo('https://discord.com/channels/1/2/3')?.requiresExternalWarning).toBe(false);
    expect(getUrlSafetyInfo('https://example.com/post/1')?.requiresExternalWarning).toBe(true);
  });
});
