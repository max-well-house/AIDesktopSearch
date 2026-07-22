const { app, BrowserWindow, ipcMain, globalShortcut } = require('electron')
const path = require('node:path')
const {
  fetchHealth,
  ensureBackend,
  stopBackend,
} = require('./backendProcess')

const RENDERER_DEV_URL = process.env.ELECTRON_RENDERER_URL || 'http://127.0.0.1:5173'
const LAUNCHER_SHORTCUT = 'Alt+Space'
const LAUNCHER_SHORTCUT_FALLBACK = 'Control+Shift+Space'

let mainWindow = null

ipcMain.handle('api:health', async () => fetchHealth())

function showLauncher() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow()
    return
  }
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.show()
  mainWindow.focus()
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (!app.isPackaged && process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(RENDERER_DEV_URL)
  } else {
    // Packaged + `npm start`: load built assets from the app root (works with asar).
    mainWindow.loadFile(path.join(app.getAppPath(), 'frontend/dist/index.html'))
  }
}

function registerLauncherShortcut() {
  const registered = globalShortcut.register(LAUNCHER_SHORTCUT, showLauncher)
  if (registered) {
    console.log(`Global shortcut registered: ${LAUNCHER_SHORTCUT}`)
    return LAUNCHER_SHORTCUT
  }

  const fallbackOk = globalShortcut.register(LAUNCHER_SHORTCUT_FALLBACK, showLauncher)
  if (fallbackOk) {
    console.warn(
      `Failed to register ${LAUNCHER_SHORTCUT}; using fallback ${LAUNCHER_SHORTCUT_FALLBACK}`,
    )
    return LAUNCHER_SHORTCUT_FALLBACK
  }

  console.warn(
    `Failed to register global shortcuts ${LAUNCHER_SHORTCUT} and ${LAUNCHER_SHORTCUT_FALLBACK}`,
  )
  return null
}

app.whenReady().then(async () => {
  await ensureBackend()
  createWindow()
  registerLauncherShortcut()

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

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
})
