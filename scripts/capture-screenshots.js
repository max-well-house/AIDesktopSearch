/**
 * Capture launcher screenshots for docs (#37).
 * Usage: npm run build && electron scripts/capture-screenshots.js
 */
const { app, BrowserWindow } = require('electron')
const fs = require('node:fs')
const path = require('node:path')

const OUT_DIR = path.join(__dirname, '..', 'docs', 'screenshots')
const INDEX = path.join(__dirname, '..', 'frontend', 'dist', 'index.html')

async function wait(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms))
}

async function capture(win, filename) {
  const image = await win.webContents.capturePage()
  const dest = path.join(OUT_DIR, filename)
  fs.writeFileSync(dest, image.toPNG())
  console.log('wrote', dest)
}

app.whenReady().then(async () => {
  if (!fs.existsSync(INDEX)) {
    console.error('FAIL: frontend/dist missing — run npm run build first')
    app.exit(1)
    return
  }

  fs.mkdirSync(OUT_DIR, { recursive: true })

  const win = new BrowserWindow({
    width: 720,
    height: 480,
    show: true,
    backgroundColor: '#0D1117',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  await win.loadFile(INDEX)
  await wait(1800)
  await capture(win, 'launcher-idle.png')

  await win.webContents.executeJavaScript(`
    (() => {
      const input = document.querySelector('input');
      if (!input) throw new Error('search input not found');
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        'value',
      ).set;
      setter.call(input, 'quarterly report');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    })()
  `)
  await wait(600)
  await capture(win, 'launcher-searching.png')

  console.log('PASS')
  app.exit(0)
})
