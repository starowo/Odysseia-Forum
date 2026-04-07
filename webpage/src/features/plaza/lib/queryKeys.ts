import type { PlazaRailKey } from '@/features/plaza/api/plazaApi';
import type { DiscoveryPreferenceRequestPatch } from '@/features/preferences/lib/discoveryPreferences';

export const plazaKeys = {
  all: ['plaza'] as const,
  banners: () => [...plazaKeys.all, 'banners'] as const,
  booklists: () => [...plazaKeys.all, 'booklists'] as const,
  rail: (railKey: PlazaRailKey, preferencePatch: DiscoveryPreferenceRequestPatch | null) => [
    ...plazaKeys.all,
    'rail',
    railKey,
    { preferencePatch },
  ] as const,
};
