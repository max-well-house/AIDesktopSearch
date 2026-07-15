const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  checkBackend: () => ipcRenderer.invoke('api:backend-status'),
})
