/**
 * Smoke-test attach mode: existing healthy server must not be killed on stop.
 * Usage: start uvicorn on :8000, then: electron scripts/test-backend-attach.js
 */
const { app } = require('electron')
const {
  ensureBackend,
  stopBackend,
  fetchHealth,
} = require('../electron/backendProcess')

app.whenReady().then(async () => {
  const before = await fetchHealth(5000)
  if (!before.ok) {
    console.error('FAIL: need a healthy server on :8000 first')
    app.exit(1)
    return
  }

  const ensured = await ensureBackend()
  console.log('ensure:', ensured)
  if (ensured.mode !== 'attached') {
    console.error('FAIL: expected mode=attached')
    app.exit(1)
    return
  }

  stopBackend()
  await new Promise((r) => setTimeout(r, 300))

  const after = await fetchHealth(5000)
  if (!after.ok) {
    console.error('FAIL: attached server was killed by stopBackend')
    app.exit(1)
    return
  }

  console.log('PASS: attached server still healthy after stopBackend')
  app.exit(0)
})
