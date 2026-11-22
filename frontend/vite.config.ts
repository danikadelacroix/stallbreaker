import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API runs on port 8000; the dev server forwards /api calls to it.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8000' } },
})
