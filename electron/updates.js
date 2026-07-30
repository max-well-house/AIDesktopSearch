/**
 * Manual update check via GitHub Releases (#137).
 * Portable-only: never auto-download or overwrite the running exe.
 */
const appConfig = require('../app.config.json')

const REPO = 'max-well-house/AIDesktopSearch'
const RELEASES_API = `https://api.github.com/repos/${REPO}/releases/latest`

function parseSemver(version) {
  const cleaned = String(version || '')
    .replace(/^v/i, '')
    .trim()
  const parts = cleaned.split('.').map((n) => Number.parseInt(n, 10))
  if (parts.length < 3 || parts.some((n) => Number.isNaN(n))) return null
  return [parts[0], parts[1], parts[2]]
}

/** @returns {number} positive if a > b */
function compareSemver(a, b) {
  for (let i = 0; i < 3; i += 1) {
    if (a[i] !== b[i]) return a[i] - b[i]
  }
  return 0
}

function pickMeshenExeAsset(assets) {
  if (!Array.isArray(assets)) return null
  const hit = assets.find((asset) => {
    const name = String(asset?.name || '')
    return /^Meshen .+\.exe$/i.test(name) || /^Meshen[- ].*\.exe$/i.test(name)
  })
  return hit?.browser_download_url || null
}

/**
 * @returns {Promise<{
 *   status: 'newer' | 'current' | 'error',
 *   current?: string,
 *   latest?: string,
 *   notes?: string,
 *   message?: string,
 *   releaseUrl?: string,
 *   downloadUrl?: string | null,
 * }>}
 */
async function checkForUpdates() {
  const current = String(appConfig.version || '')
  try {
    const response = await fetch(RELEASES_API, {
      headers: {
        Accept: 'application/vnd.github+json',
        'User-Agent': `Meshen/${current || 'desktop'}`,
      },
    })
    if (!response.ok) {
      const message =
        response.status === 403
          ? 'GitHub rate limit — try again later.'
          : `Could not reach GitHub (HTTP ${response.status}).`
      return { status: 'error', current, message }
    }

    const data = await response.json()
    const latest = String(data.tag_name || '').replace(/^v/i, '')
    const currentParts = parseSemver(current)
    const latestParts = parseSemver(latest)
    if (!currentParts || !latestParts) {
      return {
        status: 'error',
        current,
        message: 'Could not parse version numbers from the release.',
      }
    }

    const releaseUrl = data.html_url || `https://github.com/${REPO}/releases`
    const downloadUrl = pickMeshenExeAsset(data.assets)
    const notesRaw = String(data.name || '').trim() || String(data.body || '').split('\n')[0].trim()
    const notes = notesRaw ? notesRaw.slice(0, 140) : `Meshen ${latest} is available.`

    if (compareSemver(latestParts, currentParts) > 0) {
      return {
        status: 'newer',
        current,
        latest,
        notes,
        releaseUrl,
        downloadUrl,
      }
    }

    return {
      status: 'current',
      current,
      latest,
      message: `You're on the latest version (${current}).`,
    }
  } catch {
    return {
      status: 'error',
      current,
      message: 'Offline or unreachable — check your connection and try again.',
    }
  }
}

module.exports = {
  checkForUpdates,
  parseSemver,
  compareSemver,
}
