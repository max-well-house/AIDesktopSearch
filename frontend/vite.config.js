const { defineConfig } = require('vite')
const react = require('@vitejs/plugin-react')
const path = require('node:path')
const appConfig = require('../app.config.json')

module.exports = defineConfig({
  root: path.resolve(__dirname),
  base: './',
  resolve: {
    alias: {
      '@app-config': path.resolve(__dirname, '../app.config.json'),
    },
  },
  plugins: [
    react(),
    {
      name: 'app-config-html',
      transformIndexHtml(html) {
        return html
          .replace(/<title>.*?<\/title>/, `<title>${appConfig.name}</title>`)
          .replace(
            /content="#0D1117"/,
            `content="#0D1117" data-app-name="${appConfig.name}"`,
          )
      },
    },
  ],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    fs: {
      allow: [path.resolve(__dirname, '..')],
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
