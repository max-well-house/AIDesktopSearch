/**
 * Tiny JSON prefs in Electron userData.
 * Keep keys small; open-at-login stays on Electron login-item APIs.
 */
const fs = require('node:fs')
const path = require('node:path')
const { app } = require('electron')

const DEFAULT_LAUNCHER_SHORTCUT = 'Alt+Space'

const DEFAULTS = {
  preferSemanticSearch: true,
  launcherShortcut: DEFAULT_LAUNCHER_SHORTCUT,
}

function prefsPath() {
  return path.join(app.getPath('userData'), 'prefs.json')
}

function readPrefs() {
  try {
    const raw = fs.readFileSync(prefsPath(), 'utf8')
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object') {
      return { ...DEFAULTS, ...parsed }
    }
  } catch {
    // missing or corrupt → defaults
  }
  return { ...DEFAULTS }
}

function writePrefs(next) {
  const merged = { ...DEFAULTS, ...readPrefs(), ...next }
  fs.writeFileSync(prefsPath(), `${JSON.stringify(merged, null, 2)}\n`, 'utf8')
  return merged
}

function getPreferSemanticSearch() {
  return Boolean(readPrefs().preferSemanticSearch)
}

function setPreferSemanticSearch(enabled) {
  return writePrefs({ preferSemanticSearch: Boolean(enabled) }).preferSemanticSearch
}

function getLauncherShortcut() {
  const value = readPrefs().launcherShortcut
  return typeof value === 'string' && value.trim() ? value.trim() : DEFAULT_LAUNCHER_SHORTCUT
}

function setLauncherShortcut(accelerator) {
  const next =
    typeof accelerator === 'string' && accelerator.trim()
      ? accelerator.trim()
      : DEFAULT_LAUNCHER_SHORTCUT
  return writePrefs({ launcherShortcut: next }).launcherShortcut
}

module.exports = {
  DEFAULT_LAUNCHER_SHORTCUT,
  getPreferSemanticSearch,
  setPreferSemanticSearch,
  getLauncherShortcut,
  setLauncherShortcut,
}
