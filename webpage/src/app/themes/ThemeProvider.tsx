import { ReactNode, useEffect, useRef } from 'react';
import { useTheme } from '@/shared/hooks/useTheme';
import { useThemeSettings } from '@/shared/hooks/useSettings';

const loadedFontLinks = new Map<string, HTMLLinkElement>();

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const { theme, currentTheme } = useTheme();
  const settings = useThemeSettings();
  const previousThemeRef = useRef<string | null>(null);

  useEffect(() => {
    if (typeof document === 'undefined') return;

    const root = document.documentElement;
    const colors = theme.colors;
    const fontFamily = settings.fontMode === 'theme' ? theme.font?.family : null;
    const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
    const mixWithTransparency = (color: string, transparencyPercent: number) =>
      `color-mix(in srgb, ${color}, transparent ${clamp(transparencyPercent, 0, 100)}%)`;

    // 仅在“主题切换”时做全局过渡，避免拖动透明度/磨砂滑杆时整页闪烁
    const shouldAnimateThemeTransition =
      previousThemeRef.current !== null && previousThemeRef.current !== currentTheme;

    if (shouldAnimateThemeTransition) {
      root.classList.add('od-theme-transition');
    }

    const timeoutId = window.setTimeout(() => {
      root.classList.remove('od-theme-transition');
    }, shouldAnimateThemeTransition ? 380 : 0);

    root.style.setProperty('--od-text-primary', colors.textPrimary);
    root.style.setProperty('--od-text-secondary', colors.textSecondary);
    root.style.setProperty('--od-text-tertiary', colors.textTertiary);
    root.style.setProperty('--od-text-heading', colors.textHeading);
    root.style.setProperty('--od-text-label', colors.textLabel);
    root.style.setProperty('--od-text-meta', colors.textMeta);
    root.style.setProperty('--od-text-link', colors.textLink);
    root.style.setProperty('--od-text-value', colors.textValue);
    root.style.setProperty('--od-text-emphasis', colors.textEmphasis);
    root.style.setProperty('--od-accent', colors.accent);
    root.style.setProperty('--od-accent-hover', colors.accentHover);
    root.style.setProperty('--od-link', colors.link);
    root.style.setProperty('--od-link-hover', colors.linkHover);
    root.style.setProperty('--od-border', colors.border);
    root.style.setProperty('--od-border-strong', colors.borderStrong);
    root.style.setProperty('--od-success', colors.success);
    root.style.setProperty('--od-warning', colors.warning);
    root.style.setProperty('--od-error', colors.error);
    root.style.setProperty('--od-info', colors.info);
    const blurPx = Math.max(0, Math.min(32, settings.glassBlur));
    root.style.setProperty('--od-glass-blur', `${blurPx}px`);

    root.style.setProperty('--od-type-title', theme.typography.typeScaleTitle);
    root.style.setProperty('--od-type-section', 'clamp(1.2rem, 1.05rem + 0.55vw, 1.65rem)');
    root.style.setProperty('--od-type-hero', 'clamp(2rem, 1.4rem + 2vw, 3.5rem)');
    root.style.setProperty('--od-type-label', theme.typography.typeScaleLabel);
    root.style.setProperty('--od-type-body', theme.typography.typeScaleBody);
    root.style.setProperty('--od-type-meta', theme.typography.typeScaleMeta);
    root.style.setProperty('--od-type-code', theme.typography.typeScaleCode);
    root.style.setProperty('--od-weight-strong', theme.typography.fontWeightStrong);
    root.style.setProperty('--od-weight-medium', theme.typography.fontWeightMedium);
    root.style.setProperty('--od-weight-regular', theme.typography.fontWeightRegular);
    root.style.setProperty(
      '--font-sans',
      fontFamily
        ? `'${fontFamily}', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`
        : "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    );

    if (typeof document !== 'undefined') {
      const head = document.head;
      if (fontFamily && theme.font?.url) {
        if (!loadedFontLinks.has(theme.font.url)) {
          const link = document.createElement('link');
          link.rel = 'stylesheet';
          link.href = theme.font.url;
          link.setAttribute('data-od-font', fontFamily);
          head.appendChild(link);
          loadedFontLinks.set(theme.font.url, link);
        }
      }
    }

    const wallpaperUrl = settings.backgroundImageBase64?.trim() || settings.backgroundImageUrl.trim();
    const hasWallpaperSource = wallpaperUrl.length > 0;
    const hasWallpaper = settings.backgroundImageEnabled && hasWallpaperSource;
    const supportsBackdrop = typeof CSS !== 'undefined' && CSS.supports('backdrop-filter: blur(1px)');
    const glassEnabled =
      hasWallpaper &&
      (settings.glassMode === 'on' || (settings.glassMode === 'auto' && supportsBackdrop));

    if (hasWallpaper) {
      // Engram-like algorithmic transparency:
      // - only surface/border tokens are transparentized
      // - text colors remain solid for readability
      // - borders keep higher opacity (resistance)
      const visible = clamp(settings.backgroundImageOpacity, 0, 1);
      const surfaceTransparency = Math.round(60 - visible * 30);
      const rootTransparency = Math.round(44 - visible * 24);
      const borderTransparency = Math.round(surfaceTransparency * 0.2);
      const ghostTransparency = Math.max(surfaceTransparency + 18, 58);
      // 操作层与内容层透明度差距收敛：避免内容区明显偏深
      // 透明主题下整体偏浅：让详情主区域更接近背景主体的亮度感
      const chromeTransparency = Math.round(clamp(surfaceTransparency + 8, 42, 60));
      const chromeSurfaceTransparency = Math.round(clamp(surfaceTransparency + 6, 40, 58));
      const contentTransparency = Math.round(clamp(surfaceTransparency + 4, 38, 56));
      // 透明度滑杆语义：0=最暗(黑遮罩最重)，100=最亮(黑遮罩最轻)
      // 降低暗化上限，透明主题默认更通透
      const dim = clamp(0.74 - visible * 0.64, 0, 0.74);

      root.style.setProperty('--od-bg', mixWithTransparency(colors.background, Math.max(rootTransparency, 4)));
      root.style.setProperty('--od-bg-secondary', mixWithTransparency(colors.backgroundSecondary, surfaceTransparency));
      root.style.setProperty('--od-bg-tertiary', mixWithTransparency(colors.backgroundTertiary, surfaceTransparency));
      root.style.setProperty('--od-card', mixWithTransparency(colors.card, surfaceTransparency));
      root.style.setProperty('--od-card-hover', mixWithTransparency(colors.cardHover, Math.max(surfaceTransparency - 8, 8)));
      root.style.setProperty('--od-border', mixWithTransparency(colors.border, borderTransparency));
      root.style.setProperty('--od-border-strong', mixWithTransparency(colors.borderStrong, Math.max(borderTransparency - 3, 4)));
      root.style.setProperty('--od-glass-bg', mixWithTransparency(colors.backgroundSecondary, Math.max(surfaceTransparency - 6, 8)));
      root.style.setProperty('--od-glass-border', mixWithTransparency(colors.borderStrong, Math.max(borderTransparency - 4, 3)));
      root.style.setProperty('--od-surface-ghost', mixWithTransparency(colors.backgroundSecondary, ghostTransparency));
      root.style.setProperty('--od-surface-ghost-hover', mixWithTransparency(colors.backgroundSecondary, Math.max(ghostTransparency - 12, 28)));
      root.style.setProperty('--od-surface-shell', mixWithTransparency(colors.backgroundSecondary, Math.max(chromeTransparency - 10, 12)));
      root.style.setProperty('--od-surface-content', mixWithTransparency(colors.background, Math.max(contentTransparency - 6, 10)));
      root.style.setProperty('--od-surface-raised', mixWithTransparency(colors.backgroundTertiary, Math.max(contentTransparency - 3, 8)));
      root.style.setProperty('--od-surface-floating', mixWithTransparency(colors.background, Math.max(contentTransparency - 12, 6)));
      root.style.setProperty('--od-surface-input', mixWithTransparency(colors.backgroundSecondary, Math.max(contentTransparency - 2, 12)));
      root.style.setProperty('--od-surface-soft', mixWithTransparency(colors.accent, 86));
      root.style.setProperty('--od-interactive-hover', mixWithTransparency(colors.textPrimary, 92));
      root.style.setProperty('--od-interactive-strong', mixWithTransparency(colors.accent, 82));
      root.style.setProperty('--od-shell-line', mixWithTransparency(colors.border, Math.max(borderTransparency + 8, 10)));
      root.style.setProperty('--od-divider', mixWithTransparency(colors.textSecondary, 72));
      root.style.setProperty('--od-divider-strong', mixWithTransparency(colors.textPrimary, 62));
      root.style.setProperty('--od-chrome-transparency', `${chromeTransparency}%`);
      root.style.setProperty('--od-chrome-surface-transparency', `${chromeSurfaceTransparency}%`);
      root.style.setProperty('--od-content-transparency', `${contentTransparency}%`);
      root.style.setProperty('--od-wallpaper-dim', String(dim));
    } else {
      root.style.setProperty('--od-bg', colors.background);
      root.style.setProperty('--od-bg-secondary', colors.backgroundSecondary);
      root.style.setProperty('--od-bg-tertiary', colors.backgroundTertiary);
      root.style.setProperty('--od-card', colors.card);
      root.style.setProperty('--od-card-hover', colors.cardHover);
      root.style.setProperty('--od-glass-bg', colors.glassBg);
      root.style.setProperty('--od-glass-border', colors.glassBorder);
      root.style.setProperty('--od-surface-ghost', colors.surfaceGhost);
      root.style.setProperty('--od-surface-ghost-hover', colors.surfaceGhostHover);
      root.style.setProperty('--od-surface-shell', `color-mix(in srgb, ${colors.backgroundSecondary} 92%, black 8%)`);
      root.style.setProperty('--od-surface-content', `color-mix(in srgb, ${colors.background} 80%, ${colors.backgroundSecondary} 20%)`);
      root.style.setProperty('--od-surface-raised', `color-mix(in srgb, ${colors.backgroundTertiary} 76%, ${colors.background} 24%)`);
      root.style.setProperty('--od-surface-floating', `color-mix(in srgb, ${colors.background} 88%, black 12%)`);
      root.style.setProperty('--od-surface-input', `color-mix(in srgb, ${colors.backgroundSecondary} 74%, transparent 26%)`);
      root.style.setProperty('--od-surface-soft', `color-mix(in srgb, ${colors.accent} 8%, transparent 92%)`);
      root.style.setProperty('--od-interactive-hover', `color-mix(in srgb, ${colors.textPrimary} 8%, transparent 92%)`);
      root.style.setProperty('--od-interactive-strong', `color-mix(in srgb, ${colors.accent} 14%, transparent 86%)`);
      root.style.setProperty('--od-shell-line', `color-mix(in srgb, ${colors.border} 76%, transparent)`);
      root.style.setProperty('--od-divider', `color-mix(in srgb, ${colors.textSecondary} 28%, transparent)`);
      root.style.setProperty('--od-divider-strong', `color-mix(in srgb, ${colors.textPrimary} 38%, transparent)`);
      root.style.setProperty('--od-chrome-transparency', '46%');
      root.style.setProperty('--od-chrome-surface-transparency', '38%');
      root.style.setProperty('--od-content-transparency', '20%');
      root.style.setProperty('--od-wallpaper-dim', '0');
    }

    if (settings.backgroundlessMode) {
      const visible = clamp(settings.backgroundImageOpacity, 0, 1);
      const backgroundlessDim = hasWallpaper ? clamp(0.82 - visible * 0.78, 0, 0.82) : 0;

      root.style.setProperty('--od-bg', 'transparent');
      root.style.setProperty('--od-bg-secondary', 'transparent');
      root.style.setProperty('--od-bg-tertiary', 'transparent');
      root.style.setProperty('--od-card', 'transparent');
      root.style.setProperty('--od-card-hover', 'transparent');
      root.style.setProperty('--od-surface-ghost', 'transparent');
      root.style.setProperty('--od-surface-ghost-hover', 'transparent');
      root.style.setProperty('--od-surface-shell', 'transparent');
      root.style.setProperty('--od-surface-content', 'transparent');
      root.style.setProperty('--od-surface-raised', 'transparent');
      root.style.setProperty('--od-surface-input', 'transparent');
      root.style.setProperty('--od-surface-soft', 'transparent');
      root.style.setProperty('--od-interactive-hover', 'color-mix(in srgb, var(--od-text-primary) 10%, transparent 90%)');
      root.style.setProperty('--od-interactive-strong', 'color-mix(in srgb, var(--od-accent) 12%, transparent 88%)');
      root.style.setProperty('--od-shell-line', 'color-mix(in srgb, var(--od-border) 42%, transparent)');
      root.style.setProperty('--od-divider', 'color-mix(in srgb, var(--od-text-secondary) 24%, transparent)');
      root.style.setProperty('--od-divider-strong', 'color-mix(in srgb, var(--od-text-primary) 30%, transparent)');
      root.style.setProperty('--od-wallpaper-dim', String(backgroundlessDim));
    }

    root.setAttribute('data-od-glass', glassEnabled ? 'on' : 'off');
    root.setAttribute('data-od-wallpaper', hasWallpaper ? 'on' : 'off');
    root.setAttribute('data-od-backgroundless', settings.backgroundlessMode ? 'on' : 'off');

    if (hasWallpaper) {
      const escapedUrl = wallpaperUrl.replace(/"/g, '\\"');
      root.style.setProperty('--od-wallpaper-image', `url("${escapedUrl}")`);
      root.style.setProperty('--od-wallpaper-opacity', '1');
    } else {
      root.style.setProperty('--od-wallpaper-image', 'none');
      root.style.setProperty('--od-wallpaper-opacity', '0');
    }

    // 方便调试：在 html 标签上标记当前主题
    root.setAttribute('data-od-theme', currentTheme);
    previousThemeRef.current = currentTheme;

    // 暴露浏览器控制台调试函数（用于排查背景图/毛玻璃未生效）
    type DebugResult = {
      theme: string;
      glass: string | null;
      wallpaper: string | null;
      wallpaperVar: string;
      wallpaperOpacity: string;
      sample: Record<string, string>;
      opaqueBlocks: Array<{ tag: string; className: string; bg: string; area: number }>;
      imageLoad: { ok: boolean; width?: number; height?: number; error?: string };
    };

    const parseAlpha = (color: string) => {
      const match = color.match(/rgba?\(([^)]+)\)/i);
      if (!match) return 1;
      const parts = match[1].split(',').map((s) => s.trim());
      if (parts.length < 4) return 1;
      const alpha = Number(parts[3]);
      return Number.isFinite(alpha) ? alpha : 1;
    };

    const extractWallpaperUrl = (cssValue: string) => {
      const m = cssValue.match(/^url\((.*)\)$/i);
      if (!m) return '';
      return m[1].replace(/^['"]|['"]$/g, '').trim();
    };

    (window as Window & {
      odDebugTheme?: () => Promise<DebugResult>;
      odDebugThemeHelp?: () => void;
    }).odDebugTheme = async () => {
      const html = document.documentElement;
      const body = document.body;
      const main = document.getElementById('main-scroll-container');
      const csHtml = getComputedStyle(html);
      const csBody = getComputedStyle(body);
      const csMain = main ? getComputedStyle(main) : null;

      const wallpaperVar = csHtml.getPropertyValue('--od-wallpaper-image').trim();
      const wallpaperOpacity = csHtml.getPropertyValue('--od-wallpaper-opacity').trim();
      const imageUrl = extractWallpaperUrl(wallpaperVar);

      const sample = {
        odBg: csHtml.getPropertyValue('--od-bg').trim(),
        odBgSecondary: csHtml.getPropertyValue('--od-bg-secondary').trim(),
        odCard: csHtml.getPropertyValue('--od-card').trim(),
        odBorder: csHtml.getPropertyValue('--od-border').trim(),
        bodyBg: csBody.backgroundColor,
        bodyBgImage: csBody.backgroundImage,
        mainBg: csMain?.backgroundColor || 'N/A',
      };

      const opaqueBlocks = Array.from(document.querySelectorAll<HTMLElement>('div,main,section,aside,header'))
        .map((el) => {
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          const area = r.width * r.height;
          return {
            el,
            bg: s.backgroundColor,
            alpha: parseAlpha(s.backgroundColor),
            area,
          };
        })
        .filter((x) => x.area > 120000 && x.alpha >= 0.98 && x.bg !== 'rgba(0, 0, 0, 0)' && x.bg !== 'transparent')
        .sort((a, b) => b.area - a.area)
        .slice(0, 10)
        .map((x) => ({
          tag: x.el.tagName.toLowerCase(),
          className: (x.el.className || '').toString().slice(0, 120),
          bg: x.bg,
          area: Math.round(x.area),
        }));

      const imageLoad = await new Promise<DebugResult['imageLoad']>((resolve) => {
        if (!imageUrl) {
          resolve({ ok: false, error: 'No wallpaper URL in --od-wallpaper-image' });
          return;
        }
        const img = new Image();
        img.onload = () => resolve({ ok: true, width: img.naturalWidth, height: img.naturalHeight });
        img.onerror = () => resolve({ ok: false, error: 'Image load failed (CORS/404/invalid URL)' });
        img.src = imageUrl;
      });

      const result: DebugResult = {
        theme: html.getAttribute('data-od-theme') || 'unknown',
        glass: html.getAttribute('data-od-glass'),
        wallpaper: html.getAttribute('data-od-wallpaper'),
        wallpaperVar,
        wallpaperOpacity,
        sample,
        opaqueBlocks,
        imageLoad,
      };

      console.group('[odDebugTheme]');
      console.log(result);
      console.table(result.sample);
      if (result.opaqueBlocks.length) {
        console.warn('Potential opaque blockers (top 10 by area):');
        console.table(result.opaqueBlocks);
      }
      console.groupEnd();

      return result;
    };

    (window as Window & { odDebugThemeHelp?: () => void }).odDebugThemeHelp = () => {
      console.log('Run: await window.odDebugTheme()');
      console.log('It checks theme vars, wallpaper load status, and possible opaque parent blockers.');
    };

    return () => {
      root.classList.remove('od-theme-transition');
      window.clearTimeout(timeoutId);
    };
  }, [theme, currentTheme, settings.fontMode, settings.backgroundImageEnabled, settings.backgroundImageOpacity, settings.backgroundImageUrl, settings.backgroundImageBase64, settings.glassMode, settings.glassBlur, settings.backgroundlessMode]);

  return <>{children}</>;
}
