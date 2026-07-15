/**
 * Smoke-test the same net.fetch path Electron uses for checkBackend.
 * Usage: electron scripts/test-backend-fetch.js
 */
const { app, net } = require('electron')

const API_URL = 'http://127.0.0.1:8000/'

async function probe(label) {
  try {
    const response = await net.fetch(API_URL, { cache: 'no-store' })
    if (!response.ok) {
      console.log(`${label}: FAIL http ${response.status}`)
      return false
    }
    const data = await response.json()
    console.log(`${label}: OK`, JSON.stringify(data))
    return true
  } catch (err) {
    console.log(`${label}: FAIL`, err.message || String(err))
    return false
  }
}

app.whenReady().then(async () => {
  const ok = await probe('backend-status')
  app.exit(ok ? 0 : 1)
})
