/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_GUILD_ID: string;
  readonly VITE_CLIENT_ID: string;
  readonly VITE_BACKEND_URL: string;
  readonly VITE_RELEASE_FEED_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare const __APP_VERSION__: string;
