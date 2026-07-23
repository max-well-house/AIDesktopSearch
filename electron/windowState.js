const fs = require('node:fs')
const path = require('node:path')
const { app } = require('electron')

const DEFAULT_BOUNDS = { width: 720, height: 480 }
const MIN_WIDTH = 480
const MIN_HEIGHT = 360

function stateFilePath() {
  return path.join(app.getPath('userData'), 'window-state.json')
}

function loadWindowSize() {
  try {
    const raw = JSON.parse(fs.readFileSync(stateFilePath(), 'utf8'))
    const width = Number(raw.width)
    const height = Number(raw.height)
    if (!Number.isFinite(width) || !Number.isFinite(height)) {
      return { ...DEFAULT_BOUNDS }
    }
    return {
      width: Math.max(MIN_WIDTH, Math.round(width)),
      height: Math.max(MIN_HEIGHT, Math.round(height)),
    }
  } catch {
    return { ...DEFAULT_BOUNDS }
  }
}

function saveWindowSize(browserWindow) {
  if (!browserWindow || browserWindow.isDestroyed()) return
  try {
    const [width, height] = browserWindow.getSize()
    fs.writeFileSync(
      stateFilePath(),
      `${JSON.stringify({ width, height }, null, 2)}\n`,
      'utf8',
    )
  } catch (err) {
    console.warn('[window-state] save failed:', err.message || err)
  }
}

function attachWindowSizePersistence(browserWindow) {
  let timer = null
  const schedule = () => {
    clearTimeout(timer)
    timer = setTimeout(() => saveWindowSize(browserWindow), 300)
  }
  browserWindow.on('resize', schedule)
  browserWindow.on('close', () => {
    clearTimeout(timer)
    saveWindowSize(browserWindow)
  })
}

module.exports = {
  DEFAULT_BOUNDS,
  MIN_WIDTH,
  MIN_HEIGHT,
  loadWindowSize,
  saveWindowSize,
  attachWindowSizePersistence,
}
