/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin for POST /chat (empty = same-origin / Vite proxy). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
