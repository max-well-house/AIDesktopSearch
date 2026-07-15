const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  checkHealth: () => ipcRenderer.invoke('api:health'),
})
