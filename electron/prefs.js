/**
 * Tiny JSON prefs in Electron userData (Wave 2 #120).
 * Keep keys small; open-at-login stays on Electron login-item APIs.
 */
const fs = require('node:fs')
const path = require('node:path')
const { app } = require('electron')

const DEFAULTS = {
  preferSemanticSearch: true,
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

module.exports = {
  getPreferSemanticSearch,
  setPreferSemanticSearch,
}
