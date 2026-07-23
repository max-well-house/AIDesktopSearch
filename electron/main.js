const { app, BrowserWindow, ipcMain, globalShortcut } = require('electron')
const path = require('node:path')
const appConfig = require('../app.config.json')
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
ipcMain.handle('launcher:hide', async () => {
  hideLauncher()
})
ipcMain.handle('launcher:show-prepared', async () => {
  if (showPrepResolve) {
    showPrepResolve()
    showPrepResolve = null
  }
})

let expectClearBeforeShow = false
let showPrepResolve = null

function showLauncher() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow()
    return
  }
  if (mainWindow.isMinimized()) mainWindow.restore()

  // After Escape: show invisible, scrub stale compositor frame, then fade in.
  if (expectClearBeforeShow) {
    void showLauncherClean()
    return
  }

  if (mainWindow.getOpacity() !== 1) mainWindow.setOpacity(1)
  mainWindow.show()
  mainWindow.focus()
}

async function showLauncherClean() {
  if (!mainWindow || mainWindow.isDestroyed()) return

  mainWindow.setOpacity(0)
  mainWindow.show()
  mainWindow.focus()

  await new Promise((resolve) => {
    showPrepResolve = resolve
    mainWindow.webContents.send('launcher:scrub-before-show')
    setTimeout(resolve, 100)
  })
  showPrepResolve = null
  expectClearBeforeShow = false

  if (!mainWindow.isDestroyed()) {
    mainWindow.setOpacity(1)
    mainWindow.focus()
  }
}

function hideLauncher() {
  if (!mainWindow || mainWindow.isDestroyed()) return
  mainWindow.hide()
}

/** Pause: hide but keep query (Alt+Space toggle). */
function pauseLauncher() {
  hideLauncher()
}

/**
 * Done (Escape): renderer clears + paints, then hides.
 * Next show uses opacity-0 scrub so reopen never flashes stale search text.
 */
function dismissLauncher() {
  if (!mainWindow || mainWindow.isDestroyed()) return
  expectClearBeforeShow = true
  mainWindow.webContents.send('launcher:dismiss')
}

/** Alt+Space: hide+keep query when focused; otherwise show/focus. */
function toggleLauncher() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow()
    return
  }
  if (mainWindow.isVisible() && mainWindow.isFocused()) {
    pauseLauncher()
    return
  }
  showLauncher()
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 720,
    height: 480,
    minWidth: 480,
    minHeight: 360,
    center: true,
    backgroundColor: '#0D1117',
    title: appConfig.name,
    icon: path.join(__dirname, '..', 'resources', 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && input.key === 'Escape') {
      event.preventDefault()
      dismissLauncher()
    }
  })

  if (!app.isPackaged && process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(RENDERER_DEV_URL)
  } else {
    // Packaged + `npm start`: load built assets from the app root (works with asar).
    mainWindow.loadFile(path.join(app.getAppPath(), 'frontend/dist/index.html'))
  }
}

function registerLauncherShortcut() {
  const registered = globalShortcut.register(LAUNCHER_SHORTCUT, toggleLauncher)
  if (registered) {
    console.log(`Global shortcut registered: ${LAUNCHER_SHORTCUT}`)
    return LAUNCHER_SHORTCUT
  }

  const fallbackOk = globalShortcut.register(LAUNCHER_SHORTCUT_FALLBACK, toggleLauncher)
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
