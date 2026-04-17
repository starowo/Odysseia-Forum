import { fileURLToPath, URL } from 'node:url';
import { readFileSync } from 'node:fs';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react-swc';
import { analyzer } from 'vite-bundle-analyzer';

const pkg = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf-8'),
) as { version?: string };

const shouldAnalyzeBundle = process.env.ANALYZE_BUNDLE === 'true';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [
      react(),
      shouldAnalyzeBundle
        ? analyzer({
            analyzerMode: 'static',
            fileName: () => 'bundle-analysis',
            openAnalyzer: false,
            summary: true,
          })
        : null,
    ].filter(Boolean),
    define: {
      __APP_VERSION__: JSON.stringify(pkg.version ?? '0.0.0'),
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@shared-types': fileURLToPath(new URL('./src/shared/types', import.meta.url)),
      },
    },
    server: {
      port: 3000,
      host: true,
      proxy: {
        '/api': {
          target: env.VITE_BACKEND_URL || 'https://forum.shimmerday.top',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/tests/setup.ts'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'html'],
        exclude: ['node_modules/', 'src/tests/setup.ts'],
      },
    },
  };
});
