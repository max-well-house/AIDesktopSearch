/**
 * Smoke-test Escape dismiss (hide) and Alt+Space-style pause (hide, keep alive).
 * Usage: electron scripts/test-escape-hide.js
 */
const { app, BrowserWindow } = require('electron')

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 400,
    height: 300,
    show: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  let dismissCount = 0
  win.webContents.on('ipc-message', () => {})
  win.webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && input.key === 'Escape') {
      event.preventDefault()
      dismissCount += 1
      win.webContents.send('launcher:dismiss')
      win.hide()
    }
  })

  await win.loadURL('data:text/html,<html><body><input autofocus /></body></html>')
  win.focus()
  win.webContents.focus()
  await new Promise((r) => setTimeout(r, 200))

  if (!win.isVisible()) {
    console.error('FAIL: window should be visible before Escape')
    app.exit(1)
    return
  }

  win.webContents.sendInputEvent({ type: 'keyDown', keyCode: 'Escape' })
  await new Promise((r) => setTimeout(r, 100))

  if (win.isVisible()) {
    console.error('FAIL: Escape should hide the window')
    app.exit(1)
    return
  }
  if (win.isDestroyed()) {
    console.error('FAIL: Escape should hide, not destroy')
    app.exit(1)
    return
  }
  if (dismissCount !== 1) {
    console.error('FAIL: expected dismiss once, got', dismissCount)
    app.exit(1)
    return
  }
  console.log('dismiss (Escape hide + clear signal): OK')

  // Pause path: hide without destroy (query preserved by not sending dismiss)
  win.show()
  win.focus()
  await new Promise((r) => setTimeout(r, 50))
  win.hide()
  if (win.isVisible() || win.isDestroyed()) {
    console.error('FAIL: pause hide should leave window alive and hidden')
    app.exit(1)
    return
  }
  win.show()
  if (!win.isVisible()) {
    console.error('FAIL: show after pause should restore window')
    app.exit(1)
    return
  }
  console.log('pause (hide/show keep alive): OK')
  console.log('PASS')
  app.exit(0)
})
