/**
 * Smoke-test Electron FastAPI lifecycle (attach / spawn / stop).
 * Usage: electron scripts/test-backend-lifecycle.js
 *
 * Expects port 8000 free and a repo .venv present.
 */
const { app } = require('electron')
const {
  ensureBackend,
  stopBackend,
  fetchHealth,
  getBackendState,
} = require('../electron/backendProcess')

app.whenReady().then(async () => {
  const before = await fetchHealth(2000)
  if (before.ok) {
    console.error('FAIL: port 8000 already in use; stop the existing server first')
    app.exit(1)
    return
  }

  const ensured = await ensureBackend()
  console.log('ensure:', ensured)
  if (ensured.mode !== 'owned') {
    console.error('FAIL: expected mode=owned, got', ensured.mode, ensured.error)
    app.exit(1)
    return
  }

  const healthy = await fetchHealth(5000)
  if (!healthy.ok) {
    console.error('FAIL: owned backend not healthy', healthy.error)
    stopBackend()
    app.exit(1)
    return
  }
  console.log('health after spawn: OK')

  stopBackend()
  // Brief settle for taskkill
  await new Promise((r) => setTimeout(r, 500))

  const after = await fetchHealth(2000)
  if (after.ok) {
    console.error('FAIL: backend still healthy after stopBackend')
    app.exit(1)
    return
  }
  console.log('health after stop: down (expected)')
  console.log('state:', getBackendState())
  console.log('PASS')
  app.exit(0)
})
