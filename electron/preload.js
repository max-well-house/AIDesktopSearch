const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  checkHealth: () => ipcRenderer.invoke('api:health'),
  getIndexStatus: () => ipcRenderer.invoke('api:index-status'),
  scanFolder: (folderPath) => ipcRenderer.invoke('api:index-scan', folderPath),
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
