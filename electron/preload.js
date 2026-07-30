const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  checkHealth: () => ipcRenderer.invoke('api:health'),
  getIndexStatus: () => ipcRenderer.invoke('api:index-status'),
  scanFolder: (folderPath) => ipcRenderer.invoke('api:index-scan', folderPath),
  removeRoot: (rootId) => ipcRenderer.invoke('api:index-root-delete', rootId),
  setRootAutoWatch: (rootId, autoWatch) =>
    ipcRenderer.invoke('api:index-root-auto-watch', rootId, autoWatch),
  wipeIndex: () => ipcRenderer.invoke('api:index-wipe'),
  embeddingsSmoke: () => ipcRenderer.invoke('api:embeddings-smoke'),
  embeddingsBackfill: () => ipcRenderer.invoke('api:embeddings-backfill'),
  embeddingsPause: () => ipcRenderer.invoke('api:embeddings-pause'),
  embeddingsResume: () => ipcRenderer.invoke('api:embeddings-resume'),
  search: (query, limit, mode) =>
    ipcRenderer.invoke('api:search', query, limit, mode),
  openPath: (filePath) => ipcRenderer.invoke('api:open-path', filePath),
  pickFolder: () => ipcRenderer.invoke('dialog:pick-folder'),
  getOpenAtLogin: () => ipcRenderer.invoke('prefs:get-open-at-login'),
  setOpenAtLogin: (enabled) =>
    ipcRenderer.invoke('prefs:set-open-at-login', enabled),
  getPreferSemanticSearch: () =>
    ipcRenderer.invoke('prefs:get-prefer-semantic'),
  setPreferSemanticSearch: (enabled) =>
    ipcRenderer.invoke('prefs:set-prefer-semantic', enabled),
  onPreferSemanticChanged: (callback) => {
    const handler = (_event, enabled) => callback(Boolean(enabled))
    ipcRenderer.on('prefs:prefer-semantic-changed', handler)
    return () =>
      ipcRenderer.removeListener('prefs:prefer-semantic-changed', handler)
  },
  checkForUpdates: () => ipcRenderer.invoke('updates:check'),
  openExternal: (url) => ipcRenderer.invoke('shell:open-external', url),
  getLauncherShortcut: () => ipcRenderer.invoke('prefs:get-launcher-shortcut'),
  setLauncherShortcut: (accelerator) =>
    ipcRenderer.invoke('prefs:set-launcher-shortcut', accelerator),
  resetLauncherShortcut: () =>
    ipcRenderer.invoke('prefs:reset-launcher-shortcut'),
  onLauncherShortcutChanged: (callback) => {
    const handler = (_event, accelerator) => callback(accelerator)
    ipcRenderer.on('prefs:launcher-shortcut-changed', handler)
    return () =>
      ipcRenderer.removeListener('prefs:launcher-shortcut-changed', handler)
  },
  hideLauncher: (opts) => ipcRenderer.invoke('launcher:hide', opts),
  notifyShowPrepared: () => ipcRenderer.invoke('launcher:show-prepared'),
  onDismiss: (callback) => {
    const handler = () => callback()
    ipcRenderer.on('launcher:dismiss', handler)
    return () => ipcRenderer.removeListener('launcher:dismiss', handler)
  },
  onScrubBeforeShow: (callback) => {
    const handler = () => callback()
    ipcRenderer.on('launcher:scrub-before-show', handler)
    return () => ipcRenderer.removeListener('launcher:scrub-before-show', handler)
  },
})
