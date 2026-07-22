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
  win: {
    icon: 'resources/icon.ico',
    artifactName: '${productName} ${version}.${ext}',
  },
}
