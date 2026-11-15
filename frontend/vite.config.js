import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Use '/FactLens/' in production for GitHub Pages deployment (https://syedairhakazmi.github.io/FactLens/),
  // and '/' for local development.
  base: process.env.VITE_BASE || (process.env.NODE_ENV === 'production' ? '/FactLens/' : '/'),
  server: {
    host: true, // Listen on 0.0.0.0 so smartphones on local Wi-Fi can open the app
    port: 5173,
  },
})