const { app, BrowserWindow, ipcMain, net } = require('electron')
const path = require('node:path')

const API_URL = 'http://127.0.0.1:8000/'
const RENDERER_DEV_URL = process.env.ELECTRON_RENDERER_URL || 'http://127.0.0.1:5173'

ipcMain.handle('api:backend-status', async () => {
  try {
    // Chromium caches GET by default; without no-store, a killed backend
    // can still look "online" from a stale cache hit.
    const response = await net.fetch(API_URL, { cache: 'no-store' })
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

  if (!app.isPackaged && process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(RENDERER_DEV_URL)
  } else {
    win.loadFile(path.join(__dirname, '../frontend/dist/index.html'))
  }
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
