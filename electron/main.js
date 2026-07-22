const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('node:path')
const {
  fetchHealth,
  ensureBackend,
  stopBackend,
} = require('./backendProcess')

const RENDERER_DEV_URL = process.env.ELECTRON_RENDERER_URL || 'http://127.0.0.1:5173'

ipcMain.handle('api:health', async () => fetchHealth())

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
    // Packaged + `npm start`: load built assets from the app root (works with asar).
    win.loadFile(path.join(app.getAppPath(), 'frontend/dist/index.html'))
  }
}

app.whenReady().then(async () => {
  await ensureBackend()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('before-quit', () => {
  stopBackend()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
