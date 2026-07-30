const path = require('node:path')
const fs = require('node:fs')
const config = require('./app.config.json')

/**
 * electron-builder config — product identity comes from app.config.json.
 * Change the display name / company / version / fileDescription there, then repackage.
 *
 * Windows property sheet:
 * - ProductName / exe basename ← `name` (productName)
 * - CompanyName / copyright ← `company` (via package.json author + copyright)
 * - Portable wrapper FileDescription ← package.json `description` (synced from
 *   `fileDescription` — never rcedit the sealed NSIS portable; that fails integrity)
 * - Unpacked Meshen.exe FileDescription ← rcedit in afterSign (afterPack is too early;
 *   winPackager resets FileDescription to productName before sign)
 * - Artifact on disk ← win.artifactName → `Meshen <version>.exe`
 * Full semver for support stays in Settings (#125), not the Explorer description.
 */

async function applyUnpackedFileDescription(exePath) {
  const fileDescription = config.fileDescription
  if (!fileDescription || !fs.existsSync(exePath)) return
  const { rcedit } = await import('rcedit')
  await rcedit(exePath, {
    'version-string': {
      FileDescription: fileDescription,
      CompanyName: config.company,
      ProductName: config.name,
    },
  })
}

module.exports = {
  appId: config.appId,
  productName: config.name,
  copyright: `Copyright © ${new Date().getFullYear()} ${config.company}`,
  directories: {
    output: 'release',
    buildResources: 'resources',
  },
  files: ['electron/**/*', 'frontend/dist/**/*', 'app.config.json', 'package.json'],
  // Staged by scripts/stage-backend-runtime.js (#111) — FastAPI sidecar, no developer .venv.
  // icon.ico must be outside asar — Tray cannot load icons from inside app.asar on Windows.
  extraResources: [
    { from: '.packaging/backend', to: 'backend' },
    { from: '.packaging/runtime', to: 'runtime' },
    { from: 'resources/icon.ico', to: 'icon.ico' },
  ],
  win: {
    icon: 'resources/icon.ico',
    artifactName: '${productName} ${version}.${ext}',
  },
  async afterSign(context) {
    if (context.electronPlatformName !== 'win32') return
    const exeName = `${context.packager.appInfo.productFilename}.exe`
    await applyUnpackedFileDescription(path.join(context.appOutDir, exeName))
  },
}
