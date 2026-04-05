// Theme token catalog (Engram-aligned)

export interface Theme {
  name: string;
  font?: {
    family: string;
    url?: string;
  };
  colors: {
    // Core surfaces
    background: string;
    backgroundSecondary: string;
    backgroundTertiary: string;
    card: string;
    cardHover: string;

    // Text
    textPrimary: string;
    textSecondary: string;
    textTertiary: string;
    textHeading: string;
    textLabel: string;
    textMeta: string;
    textLink: string;
    textValue: string;
    textEmphasis: string;

    // Accent / semantic
    accent: string;
    accentHover: string;
    link: string;
    linkHover: string;
    border: string;
    borderStrong: string;
    success: string;
    warning: string;
    error: string;
    info: string;

    // Borderless fluid / glass
    glassBg: string;
    glassBorder: string;
    glassBlur: string;
    surfaceGhost: string;
    surfaceGhostHover: string;
  };
  typography: {
    typeScaleTitle: string;
    typeScaleLabel: string;
    typeScaleBody: string;
    typeScaleMeta: string;
    typeScaleCode: string;
    fontWeightStrong: string;
    fontWeightMedium: string;
    fontWeightRegular: string;
  };
}

export const discordDarkTheme: Theme = {
  name: 'Discord Dark',
  font: {
    family: 'Inter',
    url: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&display=swap',
  },
  colors: {
    background: '#282a2e',
    backgroundSecondary: '#2b2d31',
    backgroundTertiary: '#1e1f22',
    card: '#1e1f22',
    cardHover: '#232428',
    textPrimary: '#f2f3f5',
    textSecondary: '#b5bac1',
    textTertiary: '#949ba4',
    textHeading: '#8ea1ff',
    textLabel: '#87e8ff',
    textMeta: '#949ba4',
    textLink: '#00c7fc',
    textValue: '#3ddc84',
    textEmphasis: '#ff9c63',
    accent: '#5865f2',
    accentHover: '#4752c4',
    link: '#00a8fc',
    linkHover: '#00c7fc',
    border: '#2b2d31',
    borderStrong: '#3f4147',
    success: '#23a55a',
    warning: '#f0b232',
    error: '#f23f42',
    info: '#00a8fc',
    glassBg: 'rgba(30, 31, 34, 0.58)',
    glassBorder: 'rgba(242, 243, 245, 0.12)',
    glassBlur: '16px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'rgba(242, 243, 245, 0.07)',
  },
  typography: {
    typeScaleTitle: 'clamp(1rem, 0.9rem + 0.45vw, 1.25rem)',
    typeScaleLabel: '0.875rem',
    typeScaleBody: '0.95rem',
    typeScaleMeta: '0.75rem',
    typeScaleCode: '0.83rem',
    fontWeightStrong: '650',
    fontWeightMedium: '550',
    fontWeightRegular: '430',
  },
};

export const discordLightTheme: Theme = {
  name: 'Discord Light',
  font: {
    family: 'Inter',
    url: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&display=swap',
  },
  colors: {
    background: '#f7f8fb',
    backgroundSecondary: '#eef1f6',
    backgroundTertiary: '#ffffff',
    card: '#ffffff',
    cardHover: '#f5f7fb',
    textPrimary: '#111827',
    textSecondary: '#4b5563',
    textTertiary: '#6b7280',
    textHeading: '#3147d4',
    textLabel: '#0f766e',
    textMeta: '#6b7280',
    textLink: '#2563eb',
    textValue: '#15803d',
    textEmphasis: '#c2410c',
    accent: '#5865f2',
    accentHover: '#4752c4',
    link: '#2563eb',
    linkHover: '#1d4ed8',
    border: '#dce1ea',
    borderStrong: '#c8d0de',
    success: '#16a34a',
    warning: '#d97706',
    error: '#dc2626',
    info: '#2563eb',
    glassBg: 'rgba(255, 255, 255, 0.62)',
    glassBorder: 'rgba(17, 24, 39, 0.12)',
    glassBlur: '14px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'rgba(17, 24, 39, 0.06)',
  },
  typography: {
    typeScaleTitle: 'clamp(1rem, 0.88rem + 0.35vw, 1.2rem)',
    typeScaleLabel: '0.875rem',
    typeScaleBody: '0.95rem',
    typeScaleMeta: '0.75rem',
    typeScaleCode: '0.83rem',
    fontWeightStrong: '640',
    fontWeightMedium: '540',
    fontWeightRegular: '430',
  },
};

export const claudeDarkTheme: Theme = {
  name: 'Claude Dark',
  font: {
    family: 'Newsreader',
    url: 'https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700&display=swap',
  },
  colors: {
    background: 'oklch(0.2679 0.0036 106.6427)',
    backgroundSecondary: 'oklch(0.2357 0.0024 67.7077)',
    backgroundTertiary: 'oklch(0.2213 0.0038 106.7070)',
    card: 'oklch(0.2679 0.0036 106.6427)',
    cardHover: 'oklch(0.3085 0.0035 106.6039)',
    textPrimary: 'oklch(0.8074 0.0142 93.0137)',
    textSecondary: 'oklch(0.7713 0.0169 99.0657)',
    textTertiary: 'oklch(0.625 0.012 95)',
    textHeading: 'oklch(0.6724 0.1308 38.7559)',
    textLabel: 'oklch(0.6898 0.1581 290.4107)',
    textMeta: 'oklch(0.55 0.01 96)',
    textLink: 'oklch(0.8816 0.0276 93.1280)',
    textValue: 'oklch(0.6907 0.1554 160.3454)',
    textEmphasis: 'oklch(0.7066 0.1500 48.0000)',
    accent: 'oklch(0.6724 0.1308 38.7559)',
    accentHover: 'oklch(0.5583 0.1276 42.9956)',
    link: 'oklch(0.6898 0.1581 290.4107)',
    linkHover: 'oklch(0.747 0.145 292)',
    border: 'oklch(0.8074 0.0142 93.0137 / 0.15)',
    borderStrong: 'oklch(0.8074 0.0142 93.0137 / 0.26)',
    success: 'oklch(0.6907 0.1554 160.3454)',
    warning: 'oklch(0.8816 0.0276 93.1280)',
    error: 'oklch(0.6368 0.2078 25.3313)',
    info: 'oklch(0.6898 0.1581 290.4107)',
    glassBg: 'oklch(0.2679 0.0036 106.6427 / 0.55)',
    glassBorder: 'oklch(0.8074 0.0142 93.0137 / 0.18)',
    glassBlur: '18px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'oklch(0.8074 0.0142 93.0137 / 0.08)',
  },
  typography: {
    typeScaleTitle: 'clamp(1.03rem, 0.9rem + 0.42vw, 1.25rem)',
    typeScaleLabel: '0.89rem',
    typeScaleBody: '0.96rem',
    typeScaleMeta: '0.76rem',
    typeScaleCode: '0.835rem',
    fontWeightStrong: '640',
    fontWeightMedium: '540',
    fontWeightRegular: '420',
  },
};

export const tokyoNightTheme: Theme = {
  name: 'Tokyo Night',
  font: {
    family: 'IBM Plex Sans',
    url: 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap',
  },
  colors: {
    background: '#1a1b26',
    backgroundSecondary: '#16161e',
    backgroundTertiary: '#24283b',
    card: '#24283b',
    cardHover: '#2e3248',
    textPrimary: '#a9b1d6',
    textSecondary: '#8b93b8',
    textTertiary: '#6b7399',
    textHeading: '#bb9af7',
    textLabel: '#7dcfff',
    textMeta: '#565f89',
    textLink: '#e0af68',
    textValue: '#9ece6a',
    textEmphasis: '#f7768e',
    accent: '#7aa2f7',
    accentHover: '#6b8fe3',
    link: '#7dcfff',
    linkHover: '#9ddcff',
    border: '#414868',
    borderStrong: '#4f5880',
    success: '#9ece6a',
    warning: '#e0af68',
    error: '#f7768e',
    info: '#7dcfff',
    glassBg: 'rgba(26, 27, 38, 0.6)',
    glassBorder: 'rgba(169, 177, 214, 0.16)',
    glassBlur: '18px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'rgba(169, 177, 214, 0.08)',
  },
  typography: {
    typeScaleTitle: 'clamp(1.03rem, 0.92rem + 0.42vw, 1.24rem)',
    typeScaleLabel: '0.89rem',
    typeScaleBody: '0.96rem',
    typeScaleMeta: '0.76rem',
    typeScaleCode: '0.835rem',
    fontWeightStrong: '640',
    fontWeightMedium: '540',
    fontWeightRegular: '420',
  },
};

export const catppuccinTheme: Theme = {
  name: 'Catppuccin Mocha',
  font: {
    family: 'Nunito',
    url: 'https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap',
  },
  colors: {
    background: '#1e1e2e',
    backgroundSecondary: '#181825',
    backgroundTertiary: '#313244',
    card: '#313244',
    cardHover: '#3a3b52',
    textPrimary: '#cdd6f4',
    textSecondary: '#bac2de',
    textTertiary: '#9399b2',
    textHeading: '#cba6f7',
    textLabel: '#89b4fa',
    textMeta: '#6c7086',
    textLink: '#f9e2af',
    textValue: '#a6e3a1',
    textEmphasis: '#fab387',
    accent: '#89b4fa',
    accentHover: '#74a2f7',
    link: '#89dceb',
    linkHover: '#b4f0ff',
    border: '#45475a',
    borderStrong: '#585b70',
    success: '#a6e3a1',
    warning: '#f9e2af',
    error: '#f38ba8',
    info: '#89b4fa',
    glassBg: 'rgba(30, 30, 46, 0.58)',
    glassBorder: 'rgba(205, 214, 244, 0.15)',
    glassBlur: '18px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'rgba(205, 214, 244, 0.08)',
  },
  typography: {
    typeScaleTitle: 'clamp(1.03rem, 0.92rem + 0.42vw, 1.24rem)',
    typeScaleLabel: '0.89rem',
    typeScaleBody: '0.96rem',
    typeScaleMeta: '0.76rem',
    typeScaleCode: '0.835rem',
    fontWeightStrong: '640',
    fontWeightMedium: '540',
    fontWeightRegular: '420',
  },
};

export const nordTheme: Theme = {
  name: 'Nord',
  font: {
    family: 'Manrope',
    url: 'https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap',
  },
  colors: {
    background: '#2e3440',
    backgroundSecondary: '#242933',
    backgroundTertiary: '#3b4252',
    card: '#3b4252',
    cardHover: '#434c5e',
    textPrimary: '#d8dee9',
    textSecondary: '#c5ccda',
    textTertiary: '#9aa6bf',
    textHeading: '#88c0d0',
    textLabel: '#81a1c1',
    textMeta: '#7e8ba2',
    textLink: '#ebcb8b',
    textValue: '#a3be8c',
    textEmphasis: '#d08770',
    accent: '#88c0d0',
    accentHover: '#7ab0c1',
    link: '#81a1c1',
    linkHover: '#9ab5d2',
    border: '#4c566a',
    borderStrong: '#5b667d',
    success: '#a3be8c',
    warning: '#ebcb8b',
    error: '#bf616a',
    info: '#88c0d0',
    glassBg: 'rgba(46, 52, 64, 0.58)',
    glassBorder: 'rgba(216, 222, 233, 0.14)',
    glassBlur: '16px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'rgba(216, 222, 233, 0.08)',
  },
  typography: {
    typeScaleTitle: 'clamp(1.03rem, 0.92rem + 0.42vw, 1.22rem)',
    typeScaleLabel: '0.89rem',
    typeScaleBody: '0.95rem',
    typeScaleMeta: '0.76rem',
    typeScaleCode: '0.83rem',
    fontWeightStrong: '640',
    fontWeightMedium: '540',
    fontWeightRegular: '420',
  },
};

export const everforestTheme: Theme = {
  name: 'Everforest',
  font: {
    family: 'Noto Sans',
    url: 'https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700&display=swap',
  },
  colors: {
    background: '#2d353b',
    backgroundSecondary: '#232a2e',
    backgroundTertiary: '#343f44',
    card: '#343f44',
    cardHover: '#3d484d',
    textPrimary: '#d3c6aa',
    textSecondary: '#b8ad94',
    textTertiary: '#9fa48d',
    textHeading: '#a7c080',
    textLabel: '#7fbbb3',
    textMeta: '#859289',
    textLink: '#dbbc7f',
    textValue: '#83c092',
    textEmphasis: '#e69875',
    accent: '#a7c080',
    accentHover: '#95af71',
    link: '#7fbbb3',
    linkHover: '#9fd0c8',
    border: '#4f585e',
    borderStrong: '#5d676e',
    success: '#83c092',
    warning: '#dbbc7f',
    error: '#e67e80',
    info: '#7fbbb3',
    glassBg: 'rgba(45, 53, 59, 0.58)',
    glassBorder: 'rgba(211, 198, 170, 0.14)',
    glassBlur: '16px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'rgba(211, 198, 170, 0.08)',
  },
  typography: {
    typeScaleTitle: 'clamp(1.03rem, 0.92rem + 0.42vw, 1.22rem)',
    typeScaleLabel: '0.89rem',
    typeScaleBody: '0.95rem',
    typeScaleMeta: '0.76rem',
    typeScaleCode: '0.83rem',
    fontWeightStrong: '640',
    fontWeightMedium: '540',
    fontWeightRegular: '420',
  },
};

export const sakuraDayTheme: Theme = {
  name: 'Sakura Day',
  font: {
    family: 'Noto Serif SC',
    url: 'https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&display=swap',
  },
  colors: {
    background: '#fcf0f4',
    backgroundSecondary: '#f5e4e9',
    backgroundTertiary: '#fff7f9',
    card: '#fff7f9',
    cardHover: '#fcedf1',
    textPrimary: '#543b42',
    textSecondary: '#85666f',
    textTertiary: '#b3959e',
    textHeading: '#d65c80',
    textLabel: '#94ad18',
    textMeta: '#a38c93',
    textLink: '#3976dc',
    textValue: '#94ad18',
    textEmphasis: '#d65c80',
    accent: '#e66a8f',
    accentHover: '#cc5a7b',
    link: '#3976dc',
    linkHover: '#2a5ab3',
    border: '#e8ced5',
    borderStrong: '#d6b2bc',
    success: '#94ad18',
    warning: '#d99e52',
    error: '#d9545c',
    info: '#3976dc',
    glassBg: 'rgba(252, 240, 244, 0.65)',
    glassBorder: 'rgba(230, 106, 143, 0.15)',
    glassBlur: '16px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'rgba(230, 106, 143, 0.06)',
  },
  typography: {
    typeScaleTitle: 'clamp(1.2rem, 1rem + 0.5vw, 1.5rem)',
    typeScaleLabel: '0.95rem',
    typeScaleBody: '0.95rem',
    typeScaleMeta: '0.8rem',
    typeScaleCode: '0.85rem',
    fontWeightStrong: '700',
    fontWeightMedium: '600',
    fontWeightRegular: '400',
  },
};

export const yozakuraNightTheme: Theme = {
  name: 'Yozakura Night',
  font: {
    family: 'Marcellus',
    url: 'https://fonts.googleapis.com/css2?family=Marcellus&display=swap',
  },
  colors: {
    background: '#14101f',
    backgroundSecondary: '#1b152b',
    backgroundTertiary: '#231b36',
    card: '#1e172e',
    cardHover: '#271e3b',
    textPrimary: '#f0f4f8',
    textSecondary: '#b4c0d1',
    textTertiary: '#7d8a9e',
    textHeading: '#e699ff',
    textLabel: '#7ae0d2',
    textMeta: '#5f576b',
    textLink: '#6bc4ff',
    textValue: '#e699ff',
    textEmphasis: '#ff7be8',
    accent: '#db7cf0',
    accentHover: '#eb9dfa',
    link: '#6bc4ff',
    linkHover: '#96d8ff',
    border: '#322747',
    borderStrong: '#44375c',
    success: '#5ce0aa',
    warning: '#ebe378',
    error: '#fa558a',
    info: '#6bc4ff',
    glassBg: 'rgba(20, 16, 31, 0.65)',
    glassBorder: 'rgba(219, 124, 240, 0.15)',
    glassBlur: '18px',
    surfaceGhost: 'transparent',
    surfaceGhostHover: 'rgba(219, 124, 240, 0.08)',
  },
  typography: {
    typeScaleTitle: 'clamp(1.2rem, 1rem + 0.5vw, 1.5rem)',
    typeScaleLabel: '0.95rem',
    typeScaleBody: '0.95rem',
    typeScaleMeta: '0.8rem',
    typeScaleCode: '0.85rem',
    fontWeightStrong: '700',
    fontWeightMedium: '600',
    fontWeightRegular: '400',
  },
};

export const defaultTheme = discordDarkTheme;

export const themes = {
  discordDark: discordDarkTheme,
  discordLight: discordLightTheme,
  claudeDark: claudeDarkTheme,
  tokyoNight: tokyoNightTheme,
  catppuccin: catppuccinTheme,
  nord: nordTheme,
  everforest: everforestTheme,
  sakuraDay: sakuraDayTheme,
  yozakuraNight: yozakuraNightTheme,
} as const;

export type ThemeName = keyof typeof themes;
