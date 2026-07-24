const { app, BrowserWindow, ipcMain, globalShortcut, Tray, Menu, nativeImage, dialog, shell } = require('electron')
const path = require('node:path')
const fs = require('node:fs')
const appConfig = require('../app.config.json')
const {
  fetchHealth,
  fetchIndexStatus,
  postIndexScan,
  deleteIndexRoot,
  fetchSearch,
  ensureBackend,
  stopBackend,
} = require('./backendProcess')
const {
  DEFAULT_BOUNDS,
  MIN_WIDTH,
  MIN_HEIGHT,
  clearSavedWindowSize,
} = require('./windowState')

const RENDERER_DEV_URL = process.env.ELECTRON_RENDERER_URL || 'http://127.0.0.1:5173'
const LAUNCHER_SHORTCUT = 'Alt+Space'
const LAUNCHER_SHORTCUT_FALLBACK = 'Control+Shift+Space'
const ICON_PATH = path.join(__dirname, '..', 'resources', 'icon.ico')

let mainWindow = null
let tray = null
let isQuitting = false

ipcMain.handle('api:health', async () => fetchHealth())
ipcMain.handle('api:index-status', async () => fetchIndexStatus())
ipcMain.handle('api:index-scan', async (_event, folderPath) => {
  if (!folderPath || typeof folderPath !== 'string') {
    return { ok: false, error: 'Folder path required', url: null }
  }
  return postIndexScan(folderPath)
})
ipcMain.handle('api:index-root-delete', async (_event, rootId) => {
  const id = Number(rootId)
  if (!Number.isInteger(id) || id < 1) {
    return { ok: false, error: 'Valid root id required', url: null }
  }
  return deleteIndexRoot(id)
})
ipcMain.handle('api:search', async (_event, query, limit) => {
  const q = query == null ? '' : String(query)
  const capped = limit == null ? 50 : Number(limit)
  if (!Number.isFinite(capped) || capped < 1) {
    return { ok: false, error: 'Valid limit required', url: null }
  }
  return fetchSearch(q, Math.min(Math.floor(capped), 200))
})
ipcMain.handle('api:open-path', async (_event, filePath) => {
  if (!filePath || typeof filePath !== 'string') {
    return { ok: false, error: 'File path required' }
  }
  const resolved = path.resolve(filePath)
  if (!fs.existsSync(resolved)) {
    return { ok: false, error: 'File not found' }
  }
  try {
    const openError = await shell.openPath(resolved)
    if (openError) {
      return { ok: false, error: openError }
    }
    return { ok: true }
  } catch (err) {
    return { ok: false, error: err.message || String(err) }
  }
})
ipcMain.handle('dialog:pick-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow ?? undefined, {
    title: 'Choose a folder to index',
    properties: ['openDirectory'],
  })
  if (result.canceled || !result.filePaths?.length) {
    return { ok: false, canceled: true, path: null }
  }
  return { ok: true, canceled: false, path: result.filePaths[0] }
})
ipcMain.handle('launcher:hide', async (_event, opts) => {
  if (opts && opts.scrubNextShow) expectClearBeforeShow = true
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

/** Pause: hide but keep query (Alt+Space toggle / tray click). */
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

function shouldStartHidden() {
  if (process.argv.includes('--hidden')) return true
  try {
    // Must pass the same path/args used when registering (Windows).
    return Boolean(app.getLoginItemSettings(loginItemPathArgs()).wasOpenedAsHidden)
  } catch {
    return false
  }
}

/** path/args must match setLoginItemSettings or Windows getLoginItemSettings lies. */
function loginItemPathArgs() {
  if (app.isPackaged) {
    return { path: process.execPath, args: [] }
  }
  return { path: process.execPath, args: [app.getAppPath(), '--hidden'] }
}

function loginItemOptions(openAtLogin) {
  return {
    ...loginItemPathArgs(),
    openAtLogin: Boolean(openAtLogin),
    openAsHidden: true,
  }
}

function getOpenAtLogin() {
  try {
    return Boolean(app.getLoginItemSettings(loginItemPathArgs()).openAtLogin)
  } catch {
    return false
  }
}

function setOpenAtLogin(enabled) {
  app.setLoginItemSettings(loginItemOptions(enabled))
}

function rebuildTrayMenu() {
  if (!tray) return

  tray.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: 'Show',
        click: () => showLauncher(),
      },
      {
        label: 'Start with Windows',
        type: 'checkbox',
        checked: getOpenAtLogin(),
        click: (menuItem) => {
          setOpenAtLogin(menuItem.checked)
          // Rebuild so checked state is re-read with matching path/args.
          rebuildTrayMenu()
        },
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          isQuitting = true
          app.quit()
        },
      },
    ]),
  )
}

function createTray() {
  if (tray) return

  const icon = nativeImage.createFromPath(ICON_PATH)
  tray = new Tray(icon.isEmpty() ? ICON_PATH : icon)
  tray.setToolTip(appConfig.name)
  rebuildTrayMenu()
  tray.on('click', () => {
    // Tray click steals focus before this runs, so do not use isFocused()
    // (that would only show/refocus and never hide).
    if (!mainWindow || mainWindow.isDestroyed()) {
      createWindow()
      return
    }
    if (mainWindow.isVisible()) {
      pauseLauncher()
      return
    }
    showLauncher()
  })
}

function createWindow({ show = true } = {}) {
  mainWindow = new BrowserWindow({
    width: DEFAULT_BOUNDS.width,
    height: DEFAULT_BOUNDS.height,
    minWidth: MIN_WIDTH,
    minHeight: MIN_HEIGHT,
    center: true,
    show,
    backgroundColor: '#0D1117',
    title: appConfig.name,
    icon: ICON_PATH,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.on('close', (event) => {
    if (isQuitting) return
    event.preventDefault()
    hideLauncher()
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
  clearSavedWindowSize()
  await ensureBackend()
  const startHidden = shouldStartHidden()
  createWindow({ show: !startHidden })
  createTray()
  registerLauncherShortcut()

  if (startHidden) {
    hideLauncher()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else {
      showLauncher()
    }
  })
})

app.on('before-quit', () => {
  isQuitting = true
  clearSavedWindowSize()
  if (tray) {
    tray.destroy()
    tray = null
  }
  stopBackend()
})

// Tray keeps the process alive while the window is hidden (not destroyed).
app.on('window-all-closed', () => {
  if (process.platform === 'darwin') return
  // Do not quit — tray + hidden window are the steady state on Windows.
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
})
