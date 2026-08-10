import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Split the framework out of the app bundle. React/React-DOM/Router change
    // rarely, so giving them their own long-cached chunk means a content deploy
    // no longer forces returning visitors to re-download ~130 kB of framework.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (/react-dom|[/\\]react[/\\]|scheduler/.test(id)) return 'vendor-react'
          if (/react-router|react-helmet/.test(id)) return 'vendor-router'
          return 'vendor'
        },
      },
    },
    // Surface genuinely oversized chunks rather than warning on every build.
    chunkSizeWarningLimit: 300,
  },
})
