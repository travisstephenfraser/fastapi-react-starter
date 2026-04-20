/// <reference types="vite/client" />

// Narrow the shape of Vite's `import.meta.env` to the vars this project uses.
// Add new VITE_* vars here as they're introduced.
interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
