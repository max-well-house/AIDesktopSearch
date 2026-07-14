const { app, BrowserWindow, ipcMain, net } = require('electron')
const path = require('node:path')

const API_URL = 'http://127.0.0.1:8000/'

ipcMain.handle('api:hello', async () => {
  try {
    const response = await net.fetch(API_URL)
    if (!response.ok) {
      return {
        ok: false,
        error: `HTTP ${response.status} ${response.statusText}`,
        url: API_URL,
      }
    }
    const data = await response.json()
    return { ok: true, data, url: API_URL }
  } catch (err) {
    return {
      ok: false,
      error: err.message || String(err),
      url: API_URL,
    }
  }
})

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  win.loadFile(path.join(__dirname, 'index.html'))
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
