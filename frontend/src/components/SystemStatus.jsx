import { useEffect, useState } from 'react'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import AppMark from './brand/AppMark'

function formatCheckedAt(iso) {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString()
}

function ollamaLabel(ollama) {
  if (!ollama) return 'Unknown'
  if (ollama.status === 'available') {
    return ollama.version ? `Available (${ollama.version})` : 'Available'
  }
  if (ollama.status === 'unavailable') return 'Unavailable'
  if (ollama.status === 'not_installed') return 'Not installed'
  return 'Unknown'
}

function ollamaTone(ollama) {
  if (!ollama) return 'idle'
  if (ollama.status === 'available') return 'online'
  if (ollama.status === 'unavailable') return 'loading'
  return 'idle'
}

function formatIndexed(count) {
  if (count == null) return '—'
  if (count === 0) return '0 files'
  if (count === 1) return '1 file'
  return `${count.toLocaleString()} files`
}

/**
 * Capability / health screen from v0.1.x.
 * Kept for diagnostics; launcher is the primary surface.
 * Will move into Settings later.
 *
 * Index scan control is a thin stand-in until #40 folder management lands —
 * same System Status home, not a throwaway screen.
 */
export default function SystemStatus({ onBack }) {
  const [phase, setPhase] = useState('idle')
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState(null)
  const [url, setUrl] = useState(null)
  const [indexStatus, setIndexStatus] = useState(null)
  const [scanPath, setScanPath] = useState('')
  const [scanPhase, setScanPhase] = useState('idle')
  const [scanMessage, setScanMessage] = useState(null)

  async function refreshIndexStatus() {
    if (!window.api?.getIndexStatus) return
    const result = await window.api.getIndexStatus()
    if (result.ok) setIndexStatus(result.data)
  }

  useEffect(() => {
    void refreshIndexStatus()
  }, [])

  async function checkSystemStatus() {
    setPhase('loading')
    setError(null)
    setPayload(null)

    try {
      if (!window.api?.checkHealth) {
        setError(
          'Electron bridge missing. Use the Electron window from `npm run dev`, not a browser tab on :5173.',
        )
        setPhase('error')
        return
      }

      const result = await window.api.checkHealth()
      setUrl(result.url)

      if (result.ok) {
        setPayload(result.data)
        setPhase('online')
        await refreshIndexStatus()
        return
      }

      setError(result.error)
      setPhase('error')
    } catch (err) {
      setError(err?.message || String(err))
      setPhase('error')
    }
  }

  async function pickFolder() {
    if (!window.api?.pickFolder) return
    const result = await window.api.pickFolder()
    if (result.ok && result.path) setScanPath(result.path)
  }

  async function runScan() {
    const folder = scanPath.trim()
    if (!folder) {
      setScanMessage('Choose a folder first.')
      setScanPhase('error')
      return
    }
    if (!window.api?.scanFolder) {
      setScanMessage('Electron bridge missing for scan.')
      setScanPhase('error')
      return
    }

    setScanPhase('loading')
    setScanMessage(null)
    try {
      const result = await window.api.scanFolder(folder)
      if (!result.ok) {
        setScanPhase('error')
        setScanMessage(result.error || 'Scan failed')
        return
      }
      setIndexStatus({
        file_count: result.data.file_count,
        root_count: result.data.root_count,
        last_indexed_at: result.data.last_indexed_at,
        roots: indexStatus?.roots,
      })
      await refreshIndexStatus()
      setScanPhase('online')
      setScanMessage(
        `Saved ${result.data.files_upserted.toLocaleString()} file(s)` +
          (result.data.files_removed
            ? `, removed ${result.data.files_removed.toLocaleString()} stale`
            : '') +
          `. Index now has ${result.data.file_count.toLocaleString()} total.`,
      )
    } catch (err) {
      setScanPhase('error')
      setScanMessage(err?.message || String(err))
    }
  }

  let apiLabel = 'Not checked'
  if (phase === 'loading') apiLabel = 'Checking...'
  if (phase === 'online') apiLabel = 'Online'
  if (phase === 'error') apiLabel = 'Unable to reach backend'

  const ollama = payload?.capabilities?.ollama
  const gpu = payload?.capabilities?.gpu

  return (
    <Box className="page" component="main" sx={{ maxWidth: '32rem' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
        <AppMark size={36} />
        <Typography variant="h4" component="h1" sx={{ m: 0 }}>
          System Status
        </Typography>
      </Box>

      <p className={`status status-${phase}`}>
        <span className="status-label">Backend:</span> {apiLabel}
      </p>

      {phase === 'online' && payload && (
        <>
          <p className={`status status-${ollamaTone(ollama)}`}>
            <span className="status-label">Ollama:</span> {ollamaLabel(ollama)}
          </p>

          <dl className="details">
            <div>
              <dt>API version</dt>
              <dd>{payload.version}</dd>
            </div>
            <div>
              <dt>Last checked</dt>
              <dd>{formatCheckedAt(payload.timestamp)}</dd>
            </div>
            <div>
              <dt>GPU</dt>
              <dd>{gpu?.note || 'Not detected yet'}</dd>
            </div>
          </dl>
        </>
      )}

      <Box sx={{ mb: 2 }}>
        <p className={`status status-${indexStatus ? 'online' : 'idle'}`}>
          <span className="status-label">Index:</span>{' '}
          {formatIndexed(indexStatus?.file_count)}
          {indexStatus?.root_count
            ? ` · ${indexStatus.root_count} folder${indexStatus.root_count === 1 ? '' : 's'}`
            : ''}
        </p>
        {indexStatus?.last_indexed_at ? (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Last saved {formatCheckedAt(indexStatus.last_indexed_at)}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            No files saved yet — scan a folder to persist metadata.
          </Typography>
        )}

        <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'flex-start' }}>
          <TextField
            size="small"
            fullWidth
            label="Folder to scan"
            value={scanPath}
            onChange={(e) => setScanPath(e.target.value)}
            placeholder="C:\Users\…\Documents"
          />
          <Button variant="outlined" color="primary" onClick={pickFolder} sx={{ flexShrink: 0 }}>
            Browse…
          </Button>
        </Box>
        <Button
          variant="contained"
          color="primary"
          onClick={runScan}
          disabled={scanPhase === 'loading'}
          sx={{ mb: 1 }}
        >
          {scanPhase === 'loading' ? 'Scanning…' : 'Scan & save metadata'}
        </Button>
        {scanMessage ? (
          <Typography
            variant="body2"
            className={`status status-${scanPhase === 'error' ? 'error' : 'online'}`}
            sx={{ m: 0 }}
          >
            {scanMessage}
          </Typography>
        ) : null}
      </Box>

      {phase === 'error' && (
        <div className="error-box">
          <p>{error}</p>
          <p>
            Electron could not reach the backend at {url}.
            <br />
            Ensure first-time setup created <code>.venv</code>, or start uvicorn
            manually for debugging.
          </p>
        </div>
      )}

      <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={checkSystemStatus}
          disabled={phase === 'loading'}
        >
          Check System Status
        </Button>
        {onBack ? (
          <Button variant="outlined" color="primary" onClick={onBack}>
            Back to search
          </Button>
        ) : null}
      </Box>
    </Box>
  )
}
