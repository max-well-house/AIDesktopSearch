/**
 * Sync package.json + electron-builder fields from app.config.json.
 * Source of truth for display name, company, version — change there, not everywhere.
 */
const fs = require('node:fs')
const path = require('node:path')

const root = path.join(__dirname, '..')
const configPath = path.join(root, 'app.config.json')
const pkgPath = path.join(root, 'package.json')

const config = JSON.parse(fs.readFileSync(configPath, 'utf8'))
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'))

pkg.name = config.slug || pkg.name
pkg.version = config.version
pkg.description = config.description
pkg.author = config.company

fs.writeFileSync(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`)
console.log(
  `Synced package.json ← app.config.json (${config.name} v${config.version})`,
)
