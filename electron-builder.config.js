const path = require('node:path')
const config = require('./app.config.json')

/**
 * electron-builder config — product identity comes from app.config.json.
 * Change the display name / company / version there, then repackage.
 */
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
}
