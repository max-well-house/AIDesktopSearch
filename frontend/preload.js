const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  getHello: () => ipcRenderer.invoke('api:hello'),
})
