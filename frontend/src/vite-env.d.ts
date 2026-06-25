/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the API in production (empty in dev — Vite proxies /api). */
  readonly VITE_API_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
