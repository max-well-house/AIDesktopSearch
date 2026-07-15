const { defineConfig } = require('vite')
const react = require('@vitejs/plugin-react')
const path = require('node:path')

module.exports = defineConfig({
  root: path.resolve(__dirname),
  base: './',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
