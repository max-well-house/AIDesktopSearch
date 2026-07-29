/**
 * Stage a Windows Python runtime + backend sources for electron-builder extraResources (#111).
 * Output: .packaging/runtime (venv) and .packaging/backend (sources). Gitignored.
 */
const { execFileSync, spawnSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const root = path.join(__dirname, '..')
const packagingDir = path.join(root, '.packaging')
const runtimeDir = path.join(packagingDir, 'runtime')
const backendOut = path.join(packagingDir, 'backend')
const backendSrc = path.join(root, 'backend')
const requirements = path.join(backendSrc, 'requirements.txt')

function resolveHostPython() {
  if (process.env.AIDESKTOP_STAGE_PYTHON) {
    return process.env.AIDESKTOP_STAGE_PYTHON
  }
  const winVenv = path.join(root, '.venv', 'Scripts', 'python.exe')
  const nixVenv = path.join(root, '.venv', 'bin', 'python')
  if (process.platform === 'win32' && fs.existsSync(winVenv)) return winVenv
  if (fs.existsSync(nixVenv)) return nixVenv

  const which = process.platform === 'win32' ? 'where' : 'which'
  const probe = spawnSync(which, ['python'], { encoding: 'utf8', windowsHide: true })
  if (probe.status === 0) {
    const first = String(probe.stdout || '')
      .split(/\r?\n/)
      .map((l) => l.trim())
      .find(Boolean)
    if (first) return first
  }
  throw new Error(
    'No Python found for staging. Create .venv or set AIDESKTOP_STAGE_PYTHON.',
  )
}

function rmrf(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true })
  }
}

function shouldSkip(name) {
  return (
    name === '__pycache__' ||
    name === '.venv' ||
    name === 'venv' ||
    name.endsWith('.pyc') ||
    name.endsWith('.pyo')
  )
}

function copyBackendTree(src, dest) {
  fs.mkdirSync(dest, { recursive: true })
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (shouldSkip(entry.name)) continue
    const from = path.join(src, entry.name)
    const to = path.join(dest, entry.name)
    if (entry.isDirectory()) {
      copyBackendTree(from, to)
    } else if (entry.isFile()) {
      fs.copyFileSync(from, to)
    }
  }
}

function stagedPython() {
  if (process.platform === 'win32') {
    return path.join(runtimeDir, 'Scripts', 'python.exe')
  }
  return path.join(runtimeDir, 'bin', 'python')
}

function run(python, args, label) {
  console.log(`[stage-backend] ${label}`)
  execFileSync(python, args, {
    cwd: root,
    stdio: 'inherit',
    windowsHide: true,
    env: { ...process.env, PYTHONUTF8: '1' },
  })
}

function main() {
  if (!fs.existsSync(requirements)) {
    throw new Error(`Missing ${requirements}`)
  }
  if (!fs.existsSync(path.join(backendSrc, 'main.py'))) {
    throw new Error(`Missing ${path.join(backendSrc, 'main.py')}`)
  }

  const hostPython = resolveHostPython()
  console.log(`[stage-backend] host Python: ${hostPython}`)

  fs.mkdirSync(packagingDir, { recursive: true })
  rmrf(runtimeDir)
  rmrf(backendOut)

  run(hostPython, ['-m', 'venv', runtimeDir], `create venv → ${runtimeDir}`)

  const py = stagedPython()
  if (!fs.existsSync(py)) {
    throw new Error(`Staged python missing at ${py}`)
  }

  run(py, ['-m', 'pip', 'install', '--upgrade', 'pip'], 'upgrade pip')
  run(py, ['-m', 'pip', 'install', '-r', requirements], 'install requirements')

  console.log(`[stage-backend] copy backend → ${backendOut}`)
  copyBackendTree(backendSrc, backendOut)

  const smoke =
    'import fastapi, uvicorn, fitz, sqlite_vec, docx; print("smoke ok")'
  run(py, ['-c', smoke], 'import smoke (fastapi/uvicorn/fitz/sqlite_vec/docx)')

  console.log('[stage-backend] ready for electron-builder extraResources')
}

main()
