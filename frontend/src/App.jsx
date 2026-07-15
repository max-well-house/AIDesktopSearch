import { useState } from 'react'

function formatCheckedAt(iso) {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString()
}

export default function App() {
  const [phase, setPhase] = useState('idle')
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState(null)
  const [url, setUrl] = useState(null)

  async function testBackend() {
    setPhase('loading')
    setError(null)
    setPayload(null)

    const result = await window.api.checkBackend()
    setUrl(result.url)

    if (result.ok) {
      setPayload(result.data)
      setPhase('online')
      return
    }

    setError(result.error)
    setPhase('error')
  }

  let statusLabel = 'Not connected'
  if (phase === 'loading') statusLabel = 'Loading...'
  if (phase === 'online') statusLabel = 'Online'
  if (phase === 'error') statusLabel = 'Unable to reach backend'

  return (
    <main className="page">
      <h1>Backend Connection Test</h1>

      <p className={`status status-${phase}`}>
        <span className="status-label">Status:</span> {statusLabel}
      </p>

      {phase === 'online' && payload && (
        <dl className="details">
          <div>
            <dt>Version</dt>
            <dd>{payload.version}</dd>
          </div>
          <div>
            <dt>Last checked</dt>
            <dd>{formatCheckedAt(payload.timestamp)}</dd>
          </div>
          <div>
            <dt>Message</dt>
            <dd>{payload.message}</dd>
          </div>
        </dl>
      )}

      {phase === 'error' && (
        <div className="error-box">
          <p>{error}</p>
          <p>
            Is the backend running at {url}?
            <br />
            <code>cd backend</code>
            <br />
            <code>python -m uvicorn main:app --reload</code>
          </p>
        </div>
      )}

      <button type="button" onClick={testBackend} disabled={phase === 'loading'}>
        Test Backend
      </button>
    </main>
  )
}
