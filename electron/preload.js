const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  checkHealth: () => ipcRenderer.invoke('api:health'),
  getIndexStatus: () => ipcRenderer.invoke('api:index-status'),
  scanFolder: (folderPath) => ipcRenderer.invoke('api:index-scan', folderPath),
  removeRoot: (rootId) => ipcRenderer.invoke('api:index-root-delete', rootId),
  search: (query, limit) => ipcRenderer.invoke('api:search', query, limit),
  pickFolder: () => ipcRenderer.invoke('dialog:pick-folder'),
  hideLauncher: () => ipcRenderer.invoke('launcher:hide'),
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
