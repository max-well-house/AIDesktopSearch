import { useState } from 'react'
import Button from '@mui/material/Button'
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

/**
 * Capability / health screen from v0.1.x.
 * Kept for diagnostics; launcher is the primary surface.
 * Will move into Settings later.
 */
export default function SystemStatus({ onBack }) {
  const [phase, setPhase] = useState('idle')
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState(null)
  const [url, setUrl] = useState(null)

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
        return
      }

      setError(result.error)
      setPhase('error')
    } catch (err) {
      setError(err?.message || String(err))
      setPhase('error')
    }
  }

  let apiLabel = 'Not checked'
  if (phase === 'loading') apiLabel = 'Checking...'
  if (phase === 'online') apiLabel = 'Online'
  if (phase === 'error') apiLabel = 'Unable to reach backend'

  const ollama = payload?.capabilities?.ollama
  const gpu = payload?.capabilities?.gpu

  return (
    <Box className="page" component="main">
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
