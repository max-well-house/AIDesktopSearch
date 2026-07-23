const fs = require('node:fs')
const path = require('node:path')
const { app } = require('electron')

/** Default launcher size — used on every cold start / after Quit. */
const DEFAULT_BOUNDS = { width: 720, height: 480 }
const MIN_WIDTH = 480
const MIN_HEIGHT = 360

function stateFilePath() {
  return path.join(app.getPath('userData'), 'window-state.json')
}

/**
 * Remove any leftover cross-session size file.
 * Size is session-only: Esc / Alt+Space / tray hide keep the live window;
 * Quit (or process exit) starts at DEFAULT_BOUNDS next time.
 */
function clearSavedWindowSize() {
  try {
    fs.unlinkSync(stateFilePath())
  } catch {
    // Missing file is fine.
  }
}

module.exports = {
  DEFAULT_BOUNDS,
  MIN_WIDTH,
  MIN_HEIGHT,
  clearSavedWindowSize,
}
