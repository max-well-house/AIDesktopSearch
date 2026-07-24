import { useEffect, useState } from 'react'
import Accordion from '@mui/material/Accordion'
import AccordionDetails from '@mui/material/AccordionDetails'
import AccordionSummary from '@mui/material/AccordionSummary'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import AppMark from './brand/AppMark'
import { colors } from '../theme'

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

function ExpandIcon() {
  return (
    <Box
      component="span"
      aria-hidden
      sx={{
        display: 'inline-block',
        width: 0,
        height: 0,
        borderLeft: '5px solid transparent',
        borderRight: '5px solid transparent',
        borderTop: `6px solid ${colors.textSecondary}`,
      }}
    />
  )
}

/**
 * Capability / health screen from v0.1.x.
 * Kept for diagnostics; launcher is the primary surface.
 * Will move into Settings later.
 *
 * Indexed folders (#40): add / rescan / remove opt-in corpus roots.
 * This page scrolls; launcher stays non-scrolling.
 */
export default function SystemStatus({ onBack }) {
  const [phase, setPhase] = useState('idle')
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState(null)
  const [url, setUrl] = useState(null)
  const [indexStatus, setIndexStatus] = useState(null)
  const [busyKey, setBusyKey] = useState(null)
  const [corpusMessage, setCorpusMessage] = useState(null)
  const [corpusTone, setCorpusTone] = useState('online')
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false)

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
        setDiagnosticsOpen(true)
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
      setDiagnosticsOpen(true)
    } catch (err) {
      setError(err?.message || String(err))
      setPhase('error')
      setDiagnosticsOpen(true)
    }
  }

  function setCorpusFeedback(tone, message) {
    setCorpusTone(tone)
    setCorpusMessage(message)
  }

  async function addFolder() {
    if (!window.api?.pickFolder || !window.api?.scanFolder) {
      setCorpusFeedback('error', 'Electron bridge missing for folder management.')
      return
    }

    const picked = await window.api.pickFolder()
    if (picked.canceled || !picked.ok || !picked.path) return

    setBusyKey('add')
    setCorpusMessage(null)
    try {
      const result = await window.api.scanFolder(picked.path)
      if (!result.ok) {
        setCorpusFeedback('error', result.error || 'Scan failed')
        return
      }
      await refreshIndexStatus()
      setCorpusFeedback(
        'online',
        `Added ${result.data.root_path} — saved ${result.data.files_upserted.toLocaleString()} file(s).`,
      )
    } catch (err) {
      setCorpusFeedback('error', err?.message || String(err))
    } finally {
      setBusyKey(null)
    }
  }

  async function rescanRoot(root) {
    if (!window.api?.scanFolder) {
      setCorpusFeedback('error', 'Electron bridge missing for scan.')
      return
    }

    setBusyKey(`scan-${root.id}`)
    setCorpusMessage(null)
    try {
      const result = await window.api.scanFolder(root.path)
      if (!result.ok) {
        setCorpusFeedback('error', result.error || 'Rescan failed')
        return
      }
      await refreshIndexStatus()
      setCorpusFeedback(
        'online',
        `Rescanned — saved ${result.data.files_upserted.toLocaleString()} file(s)` +
          (result.data.files_removed
            ? `, removed ${result.data.files_removed.toLocaleString()} stale`
            : '') +
          '.',
      )
    } catch (err) {
      setCorpusFeedback('error', err?.message || String(err))
    } finally {
      setBusyKey(null)
    }
  }

  async function removeRoot(root) {
    if (!window.api?.removeRoot) {
      setCorpusFeedback('error', 'Electron bridge missing for remove.')
      return
    }

    setBusyKey(`remove-${root.id}`)
    setCorpusMessage(null)
    try {
      const result = await window.api.removeRoot(root.id)
      if (!result.ok) {
        setCorpusFeedback('error', result.error || 'Remove failed')
        return
      }
      await refreshIndexStatus()
      setCorpusFeedback(
        'online',
        `Removed ${result.data.root_path} (${result.data.files_removed.toLocaleString()} file(s) cleared).`,
      )
    } catch (err) {
      setCorpusFeedback('error', err?.message || String(err))
    } finally {
      setBusyKey(null)
    }
  }

  let apiLabel = 'Not checked'
  if (phase === 'loading') apiLabel = 'Checking...'
  if (phase === 'online') apiLabel = 'Online'
  if (phase === 'error') apiLabel = 'Unable to reach backend'

  const ollama = payload?.capabilities?.ollama
  const gpu = payload?.capabilities?.gpu
  const roots = indexStatus?.roots ?? []
  const busy = busyKey != null

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        WebkitOverflowScrolling: 'touch',
      }}
    >
      <Box className="page" component="main" sx={{ maxWidth: '36rem', pb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
          <AppMark size={36} />
          <Typography variant="h4" component="h1" sx={{ m: 0 }}>
            System Status
          </Typography>
        </Box>

        <Box sx={{ mb: 2 }}>
          <p className={`status status-${indexStatus ? 'online' : 'idle'}`}>
            <span className="status-label">Index:</span>{' '}
            {formatIndexed(indexStatus?.file_count)}
            {indexStatus?.root_count
              ? ` · ${indexStatus.root_count} folder${indexStatus.root_count === 1 ? '' : 's'}`
              : ''}
          </p>
          {indexStatus?.last_indexed_at ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Last saved {formatCheckedAt(indexStatus.last_indexed_at)}
            </Typography>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              No folders indexed yet — add one below.
            </Typography>
          )}

          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Only folders you add are indexed. Whole-PC / whole-disk crawling is out
            of scope for defaults.
          </Typography>

          <Typography
            variant="subtitle2"
            sx={{ mb: 1, color: colors.textPrimary, fontWeight: 600 }}
          >
            Indexed folders
          </Typography>

          {roots.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              None yet.
            </Typography>
          ) : (
            <Box
              component="ul"
              sx={{
                listStyle: 'none',
                m: 0,
                mb: 1.5,
                p: 0,
                display: 'grid',
                gap: 1,
              }}
            >
              {roots.map((root) => (
                <Box
                  component="li"
                  key={root.id}
                  sx={{
                    border: `1px solid ${colors.border}`,
                    backgroundColor: colors.surface,
                    px: 1.25,
                    py: 1,
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      color: colors.textPrimary,
                      wordBreak: 'break-all',
                      mb: 0.5,
                    }}
                  >
                    {root.path}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', mb: 1 }}
                  >
                    {formatIndexed(root.file_count)}
                    {root.last_scan_at
                      ? ` · scanned ${formatCheckedAt(root.last_scan_at)}`
                      : ' · not scanned yet'}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Button
                      size="small"
                      variant="outlined"
                      color="primary"
                      disabled={busy}
                      onClick={() => rescanRoot(root)}
                    >
                      {busyKey === `scan-${root.id}` ? 'Scanning…' : 'Rescan'}
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      disabled={busy}
                      onClick={() => removeRoot(root)}
                    >
                      {busyKey === `remove-${root.id}` ? 'Removing…' : 'Remove'}
                    </Button>
                  </Box>
                </Box>
              ))}
            </Box>
          )}

          <Button
            variant="contained"
            color="primary"
            onClick={addFolder}
            disabled={busy}
            sx={{ mb: 1 }}
          >
            {busyKey === 'add' ? 'Adding…' : 'Add folder…'}
          </Button>
          {corpusMessage ? (
            <Typography
              variant="body2"
              className={`status status-${corpusTone === 'error' ? 'error' : 'online'}`}
              sx={{ m: 0 }}
            >
              {corpusMessage}
            </Typography>
          ) : null}
        </Box>

        <Accordion
          disableGutters
          elevation={0}
          expanded={diagnosticsOpen}
          onChange={(_event, expanded) => setDiagnosticsOpen(expanded)}
          sx={{
            mb: 2,
            backgroundColor: 'transparent',
            border: `1px solid ${colors.border}`,
            '&:before': { display: 'none' },
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandIcon />}
            sx={{
              minHeight: 44,
              px: 1.25,
              '& .MuiAccordionSummary-content': { my: 1, alignItems: 'center', gap: 1 },
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: colors.textPrimary }}>
              Diagnostics
            </Typography>
            <Typography variant="body2" color="text.secondary" component="span">
              Backend: {apiLabel}
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 1.25, pt: 0, pb: 1.5 }}>
            <p className={`status status-${phase}`} style={{ marginBottom: '0.75rem' }}>
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

            <Button
              variant="contained"
              color="primary"
              onClick={checkSystemStatus}
              disabled={phase === 'loading'}
            >
              Check System Status
            </Button>
          </AccordionDetails>
        </Accordion>

        {onBack ? (
          <Button variant="outlined" color="primary" onClick={onBack}>
            Back to search
          </Button>
        ) : null}
      </Box>
    </Box>
  )
}
