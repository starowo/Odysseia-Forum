/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        od: {
          bg: 'var(--od-bg)',
          shell: 'var(--od-surface-shell)',
          content: 'var(--od-surface-content)',
          raised: 'var(--od-surface-raised)',
          floating: 'var(--od-surface-floating)',
          input: 'var(--od-surface-input)',
          soft: 'var(--od-surface-soft)',
          hover: 'var(--od-interactive-hover)',
          accent: 'var(--od-accent)',
          accentHover: 'var(--od-accent-hover)',
          text: {
            primary: 'var(--od-text-primary)',
            secondary: 'var(--od-text-secondary)',
            tertiary: 'var(--od-text-tertiary)',
          },
          border: 'var(--od-border)',
          borderStrong: 'var(--od-border-strong)',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
      },
      fontSize: {
        'od-xs': 'var(--od-text-xs)',
        'od-sm': 'var(--od-text-sm)',
        'od-base': 'var(--od-text-base)',
        'od-lg': 'var(--od-text-lg)',
        'od-section': 'var(--od-type-section)',
        'od-hero': 'var(--od-type-hero)',
      },
      fontWeight: {
        'od-normal': 'var(--od-font-normal)',
        'od-medium': 'var(--od-font-medium)',
        'od-bold': 'var(--od-font-bold)',
      },
      spacing: {
        /* 基础间隙 */
        'od-xs': 'var(--od-space-xs)',
        'od-sm': 'var(--od-space-sm)',
        'od-md': 'var(--od-space-md)',
        'od-lg': 'var(--od-space-lg)',
        'od-xl': 'var(--od-space-xl)',
        /* 语义间隙 */
        'od-modal-p': 'var(--od-modal-p)',
        'od-card-p': 'var(--od-card-p)',
        'od-card-gap': 'var(--od-card-gap)',
        'od-list-gap': 'var(--od-list-gap)',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        shimmer: 'shimmer 2s infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
  safelist: [
    'grid-cols-1',
    'grid-cols-2',
    'grid-cols-3',
    'grid-cols-4',
    'grid-cols-5',
  ],
};
