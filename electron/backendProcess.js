const { app, net } = require('electron')
const { spawn, execFileSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const HOST = '127.0.0.1'
const PORT = 8000
const HEALTH_URL = `http://${HOST}:${PORT}/health`
const INDEX_STATUS_URL = `http://${HOST}:${PORT}/index/status`
const INDEX_SCAN_URL = `http://${HOST}:${PORT}/index/scan`
const INDEX_ROOTS_URL = `http://${HOST}:${PORT}/index/roots`
const INDEX_WIPE_URL = `http://${HOST}:${PORT}/index/wipe`
const INDEX_EMBEDDINGS_SMOKE_URL = `http://${HOST}:${PORT}/index/embeddings/smoke`
const INDEX_EMBEDDINGS_BACKFILL_URL = `http://${HOST}:${PORT}/index/embeddings/backfill`
const INDEX_EMBEDDINGS_PAUSE_URL = `http://${HOST}:${PORT}/index/embeddings/pause`
const INDEX_EMBEDDINGS_RESUME_URL = `http://${HOST}:${PORT}/index/embeddings/resume`
const SEARCH_URL = `http://${HOST}:${PORT}/search`
const SPAWN_TIMEOUT_MS = 15000
const POLL_INTERVAL_MS = 250
// /health may wait ~2s for an Ollama probe; keep headroom above that.
const PROBE_TIMEOUT_MS = 5000

async function fetchJson(url, options = {}, timeoutMs = 5000) {
  try {
    const response = await net.fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(timeoutMs),
      ...options,
    })
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`
      try {
        const body = await response.json()
        if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail
      } catch {
        // ignore parse errors
      }
      return { ok: false, error: detail, url }
    }
    const data = await response.json()
    return { ok: true, data, url }
  } catch (err) {
    return {
      ok: false,
      error: err.message || String(err),
      url,
    }
  }
}

async function fetchHealth(timeoutMs = 5000) {
  return fetchJson(HEALTH_URL, {}, timeoutMs)
}

async function fetchIndexStatus(timeoutMs = 5000) {
  return fetchJson(INDEX_STATUS_URL, {}, timeoutMs)
}

async function postIndexScan(folderPath, timeoutMs = 120000) {
  return fetchJson(
    INDEX_SCAN_URL,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: folderPath }),
    },
    timeoutMs,
  )
}

async function deleteIndexRoot(rootId, timeoutMs = 10000) {
  return fetchJson(
    `${INDEX_ROOTS_URL}/${encodeURIComponent(rootId)}`,
    { method: 'DELETE' },
    timeoutMs,
  )
}

async function patchRootAutoWatch(rootId, autoWatch, timeoutMs = 10000) {
  return fetchJson(
    `${INDEX_ROOTS_URL}/${encodeURIComponent(rootId)}/auto-watch`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_watch: Boolean(autoWatch) }),
    },
    timeoutMs,
  )
}

async function postIndexWipe(timeoutMs = 30000) {
  return fetchJson(
    INDEX_WIPE_URL,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' },
    timeoutMs,
  )
}

async function postEmbeddingsSmoke(timeoutMs = 15000) {
  return fetchJson(
    INDEX_EMBEDDINGS_SMOKE_URL,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' },
    timeoutMs,
  )
}

async function postEmbeddingsBackfill(timeoutMs = 30000) {
  return fetchJson(
    INDEX_EMBEDDINGS_BACKFILL_URL,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' },
    timeoutMs,
  )
}

async function postEmbeddingsPause(timeoutMs = 10000) {
  return fetchJson(
    INDEX_EMBEDDINGS_PAUSE_URL,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' },
    timeoutMs,
  )
}

async function postEmbeddingsResume(timeoutMs = 10000) {
  return fetchJson(
    INDEX_EMBEDDINGS_RESUME_URL,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' },
    timeoutMs,
  )
}

async function fetchSearch(query, limit = 50, mode = 'classic', timeoutMs = 15000) {
  const params = new URLSearchParams()
  params.set('q', query == null ? '' : String(query))
  if (limit != null) params.set('limit', String(limit))
  if (mode) params.set('mode', String(mode))
  return fetchJson(`${SEARCH_URL}?${params.toString()}`, {}, timeoutMs)
}

/** @type {{ mode: 'idle' | 'attached' | 'owned' | 'missing' | 'failed', child: import('node:child_process').ChildProcess | null, error: string | null }} */
let state = {
  mode: 'idle',
  child: null,
  error: null,
}

function resolvePython(root) {
  if (!root) return null
  const win = path.join(root, '.venv', 'Scripts', 'python.exe')
  const nix = path.join(root, '.venv', 'bin', 'python')
  if (process.platform === 'win32' && fs.existsSync(win)) return win
  if (fs.existsSync(nix)) return nix
  if (fs.existsSync(win)) return win
  return null
}

/** Packaged sidecar: resources/runtime + resources/backend (#111). */
function resolvePackagedBackend() {
  const resources = process.resourcesPath
  if (!resources) return null
  const backendDir = path.join(resources, 'backend')
  const python =
    process.platform === 'win32'
      ? path.join(resources, 'runtime', 'Scripts', 'python.exe')
      : path.join(resources, 'runtime', 'bin', 'python')
  if (!fs.existsSync(python)) return null
  if (!fs.existsSync(path.join(backendDir, 'main.py'))) return null
  return { python, backendDir }
}

function resolveDevBackend() {
  if (process.env.AIDESKTOP_ROOT) {
    const root = path.resolve(process.env.AIDESKTOP_ROOT)
    const python = resolvePython(root)
    if (!python) return null
    return { python, backendDir: path.join(root, 'backend'), packaged: false }
  }

  const root = path.join(__dirname, '..')
  const python = resolvePython(root)
  if (!python) return null
  return { python, backendDir: path.join(root, 'backend'), packaged: false }
}

/**
 * Resolve python + backend cwd for spawn.
 * Packaged → staged runtime under resourcesPath; unpackaged → project .venv.
 */
function resolveBackendSpawn() {
  if (app.isPackaged) {
    const packaged = resolvePackagedBackend()
    if (!packaged) return null
    return {
      ...packaged,
      packaged: true,
      env: {
        ...process.env,
        AIDESKTOP_DB: path.join(app.getPath('userData'), 'index.db'),
      },
    }
  }
  const dev = resolveDevBackend()
  if (!dev) return null
  return { ...dev, env: { ...process.env } }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function killProcessTree(pid) {
  if (!pid) return

  if (process.platform === 'win32') {
    try {
      execFileSync('taskkill', ['/pid', String(pid), '/t', '/f'], {
        stdio: 'ignore',
        windowsHide: true,
      })
    } catch {
      // Process already gone.
    }
    return
  }

  try {
    process.kill(pid, 'SIGTERM')
  } catch {
    // Process already gone.
  }
}

function stopBackend() {
  if (state.mode !== 'owned' || !state.child) {
    state.child = null
    return
  }

  const { pid } = state.child
  state.child = null
  state.mode = 'idle'
  console.log('[backend] stopping owned process', pid)
  killProcessTree(pid)
}

async function waitForHealthy(timeoutMs) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (state.child && state.child.exitCode != null) {
      return {
        ok: false,
        error: `Backend exited early (code ${state.child.exitCode})`,
        url: HEALTH_URL,
      }
    }

    const result = await fetchHealth(PROBE_TIMEOUT_MS)
    if (result.ok) return result
    await sleep(POLL_INTERVAL_MS)
  }

  return {
    ok: false,
    error: `Backend did not become healthy within ${timeoutMs}ms`,
    url: HEALTH_URL,
  }
}

async function ensureBackend() {
  const probe = await fetchHealth(PROBE_TIMEOUT_MS)
  if (probe.ok) {
    state = { mode: 'attached', child: null, error: null }
    console.log('[backend] attached to existing server at', HEALTH_URL)
    return getBackendState()
  }

  const spawnTarget = resolveBackendSpawn()
  if (!spawnTarget) {
    state = {
      mode: 'missing',
      child: null,
      error: app.isPackaged
        ? 'Packaged backend runtime is missing. Reinstall the app, or rebuild with npm run package / package:portable.'
        : 'No .venv Python found. Run first-time setup (create .venv + pip install), set AIDESKTOP_ROOT, or start uvicorn manually.',
    }
    console.warn('[backend]', state.error)
    return getBackendState()
  }

  const { python, backendDir, env } = spawnTarget
  console.log('[backend] spawning', python, 'in', backendDir)

  let child
  try {
    // No --reload: reloader parent/worker makes Windows tree cleanup unreliable.
    child = spawn(
      python,
      ['-m', 'uvicorn', 'main:app', '--host', HOST, '--port', String(PORT)],
      {
        cwd: backendDir,
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
        env,
      },
    )
  } catch (err) {
    state = {
      mode: 'failed',
      child: null,
      error: err.message || String(err),
    }
    console.error('[backend] spawn failed:', state.error)
    return getBackendState()
  }

  state = { mode: 'owned', child, error: null }

  child.stdout?.on('data', (buf) => {
    const line = String(buf).trim()
    if (line) console.log('[uvicorn]', line)
  })
  child.stderr?.on('data', (buf) => {
    const line = String(buf).trim()
    if (line) console.log('[uvicorn]', line)
  })
  child.on('exit', (code, signal) => {
    console.log('[backend] child exited', { code, signal })
    if (state.child === child) {
      state.child = null
      if (state.mode === 'owned') {
        state.mode = 'failed'
        state.error = `Backend exited (code ${code}, signal ${signal})`
      }
    }
  })
  child.on('error', (err) => {
    console.error('[backend] child error:', err.message)
    if (state.child === child) {
      state.child = null
      state.mode = 'failed'
      state.error = err.message || String(err)
    }
  })

  const ready = await waitForHealthy(SPAWN_TIMEOUT_MS)
  if (!ready.ok) {
    killProcessTree(child.pid)
    state = {
      mode: 'failed',
      child: null,
      error: ready.error || 'Backend failed to start',
    }
    console.error('[backend]', state.error)
    return getBackendState()
  }

  console.log('[backend] owned process healthy at', HEALTH_URL)
  return getBackendState()
}

function getBackendState() {
  return {
    mode: state.mode,
    error: state.error,
    url: HEALTH_URL,
  }
}

module.exports = {
  HEALTH_URL,
  fetchHealth,
  fetchIndexStatus,
  postIndexScan,
  deleteIndexRoot,
  patchRootAutoWatch,
  postIndexWipe,
  postEmbeddingsSmoke,
  postEmbeddingsBackfill,
  postEmbeddingsPause,
  postEmbeddingsResume,
  fetchSearch,
  ensureBackend,
  stopBackend,
  getBackendState,
}
