/**
 * Resize docs/brand/app-mark-dark.png into resources/ + frontend/public icons.
 * Run: npm run icons
 */
const { execFileSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const root = path.join(__dirname, '..')
const sourceMark = path.join(root, 'docs', 'brand', 'app-mark-dark.png')
const outDir = path.join(root, 'resources')
const publicDir = path.join(root, 'frontend', 'public')
const bg = '#0D1117'

if (!fs.existsSync(sourceMark)) {
  console.error(`Missing source mark: ${sourceMark}`)
  process.exit(1)
}

fs.mkdirSync(outDir, { recursive: true })

const ps = `
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = 'Stop'
$srcPath = '${sourceMark.replace(/'/g, "''")}'
$outDir = '${outDir.replace(/'/g, "''")}'
$publicDir = '${publicDir.replace(/'/g, "''")}'
$bg = [System.Drawing.ColorTranslator]::FromHtml('${bg}')

function New-Sized($size, $dest) {
  $mark = [System.Drawing.Image]::FromFile($srcPath)
  $bmp = New-Object System.Drawing.Bitmap $size, $size
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.Clear($bg)
  $g.DrawImage($mark, 0, 0, $size, $size)
  $bmp.Save($dest, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose(); $mark.Dispose()
}

foreach ($s in @(16, 24, 32, 48, 64, 128, 256)) {
  New-Sized $s (Join-Path $outDir ("icon-$s.png"))
}
New-Sized 256 (Join-Path $outDir 'icon.png')
New-Sized 256 (Join-Path $publicDir 'app-mark.png')
New-Sized 32 (Join-Path $publicDir 'favicon-32.png')
Write-Output 'resized dark icons'
`

const psPath = path.join(outDir, '_generate-icons.ps1')
fs.writeFileSync(psPath, ps)
try {
  execFileSync(
    'powershell.exe',
    ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', psPath],
    { stdio: 'inherit' },
  )
} finally {
  fs.unlinkSync(psPath)
}

async function writeIco() {
  const pngToIco = require('png-to-ico').default
  const files = [16, 24, 32, 48, 64, 128, 256].map((s) =>
    path.join(outDir, `icon-${s}.png`),
  )
  const buf = await pngToIco(files)
  fs.writeFileSync(path.join(outDir, 'icon.ico'), buf)
  for (const file of files) fs.unlinkSync(file)
  console.log('Wrote resources/icon.ico + resources/icon.png + frontend/public/app-mark.png')
}

writeIco().catch((err) => {
  console.error(err)
  process.exit(1)
})
