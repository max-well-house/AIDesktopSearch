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

function vectorStoreLabel(vectorStore) {
  if (!vectorStore) return 'Unknown'
  if (vectorStore.available) {
    return vectorStore.version
      ? `Available (sqlite-vec ${vectorStore.version})`
      : 'Available'
  }
  return vectorStore.note || 'Unavailable'
}

function vectorStoreTone(vectorStore) {
  if (!vectorStore) return 'idle'
  return vectorStore.available ? 'online' : 'loading'
}

function embeddingLabel(models) {
  if (!models) return 'Unknown'
  return models.embedding ? 'Available (nomic-embed-text)' : 'Unavailable — pull nomic-embed-text'
}

function embeddingTone(models) {
  if (!models) return 'idle'
  return models.embedding ? 'online' : 'loading'
}

function gpuLabel(gpu) {
  if (!gpu) return 'Unknown'
  if (gpu.available === true) {
    return gpu.name ? `Available (${gpu.name})` : 'Available'
  }
  if (gpu.available === false) {
    return gpu.note || 'Unavailable'
  }
  return gpu.note ? `Unknown — ${gpu.note}` : 'Unknown'
}

function gpuTone(gpu) {
  if (!gpu) return 'idle'
  if (gpu.available === true) return 'online'
  if (gpu.available === false) return 'loading'
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
  const [advancedOpen, setAdvancedOpen] = useState(false)
  /** Active Start-embedding run: baselines for done confirmation (#122). */
  const [embedRun, setEmbedRun] = useState(null)

  async function refreshIndexStatus() {
    if (!window.api?.getIndexStatus) return
    const result = await window.api.getIndexStatus()
    if (result.ok) setIndexStatus(result.data)
  }

  async function refreshHealthQuiet() {
    if (!window.api?.checkHealth) return
    try {
      const result = await window.api.checkHealth()
      if (result.ok) {
        setPayload(result.data)
        setUrl(result.url)
        setPhase('online')
      }
    } catch {
      // Keep last known snapshot during quiet polls.
    }
  }

  useEffect(() => {
    void refreshIndexStatus()
  }, [])

  // Live embed progress while the queue is draining or a started run is active (#122).
  const embedQueueDepth = indexStatus?.embed_queue_depth ?? 0
  const embedPaused = Boolean(indexStatus?.embed_paused)
  const pollEmbed =
    embedQueueDepth > 0 || (embedRun != null && embedPaused)
  useEffect(() => {
    if (!pollEmbed) return undefined
    const id = setInterval(() => {
      void refreshIndexStatus()
      void refreshHealthQuiet()
    }, 2000)
    return () => clearInterval(id)
  }, [pollEmbed])

  // Done confirmation when a started embed run finishes (#122).
  useEffect(() => {
    if (!embedRun || !indexStatus) return
    const depth = indexStatus.embed_queue_depth ?? 0
    const paused = Boolean(indexStatus.embed_paused)
    const completed =
      (indexStatus.embed_completed ?? 0) - (embedRun.baselineCompleted ?? 0)
    const failed =
      (indexStatus.embed_failed ?? 0) - (embedRun.baselineFailed ?? 0)

    if (!embedRun.wasActive) {
      if (depth > 0 || paused) {
        setEmbedRun((prev) => (prev ? { ...prev, wasActive: true } : prev))
        return
      }
      // Fast path: work finished before we observed a non-empty queue.
      if (completed <= 0 && failed <= 0) return
    } else if (depth > 0 || paused) {
      return
    }

    const chunksNow = indexStatus.embedding_chunk_count ?? 0
    const chunkDelta = Math.max(
      0,
      chunksNow - (embedRun.chunksAtStart ?? 0),
    )
    const parts = [
      `Embedded ${Math.max(0, completed).toLocaleString()} file(s)`,
    ]
    if (chunkDelta > 0) {
      parts.push(`${chunkDelta.toLocaleString()} chunk(s)`)
    }
    if (failed > 0) {
      parts.push(`${failed.toLocaleString()} failed`)
    }
    setCorpusTone(failed > 0 && completed <= 0 ? 'error' : 'online')
    setCorpusMessage(parts.join(' · '))
    setEmbedRun(null)
  }, [embedRun, indexStatus])

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

  async function verifyVectorStore() {
    if (!window.api?.embeddingsSmoke) {
      setCorpusFeedback('error', 'Electron bridge missing for vector store check.')
      return
    }
    setBusyKey('embeddings-smoke')
    setCorpusFeedback('online', 'Verifying vector store…')
    try {
      const result = await window.api.embeddingsSmoke()
      if (!result.ok) {
        setCorpusFeedback('error', result.error || 'Vector store check failed')
        return
      }
      const data = result.data
      if (!data?.ok) {
        setCorpusFeedback('error', data?.error || 'Vector store check failed')
        return
      }
      const dist =
        typeof data.distance === 'number' ? data.distance.toFixed(6) : '?'
      setCorpusFeedback(
        'online',
        `Vector store OK — self-match distance ${dist} on ${data.file_name || 'file'}`,
      )
      await refreshIndexStatus()
      if (phase === 'online') {
        const health = await window.api.checkHealth()
        if (health.ok) setPayload(health.data)
      }
    } catch (err) {
      setCorpusFeedback('error', err?.message || String(err))
    } finally {
      setBusyKey(null)
    }
  }

  async function startEmbedding() {
    if (!window.api?.embeddingsBackfill) {
      setCorpusFeedback('error', 'Electron bridge missing for Start embedding.')
      return
    }
    setBusyKey('embeddings-start')
    try {
      const baselineCompleted = indexStatus?.embed_completed ?? 0
      const baselineFailed = indexStatus?.embed_failed ?? 0
      const chunksAtStart = indexStatus?.embedding_chunk_count ?? 0
      const result = await window.api.embeddingsBackfill()
      if (!result.ok) {
        setCorpusFeedback('error', result.error || 'Start embedding failed')
        return
      }
      const data = result.data
      const enqueued = data.enqueued ?? 0
      if (enqueued <= 0) {
        setCorpusFeedback('online', 'Nothing to embed.')
        await refreshIndexStatus()
        return
      }
      setEmbedRun({
        baselineCompleted,
        baselineFailed,
        chunksAtStart,
        startedPending: enqueued,
        wasActive: false,
      })
      setCorpusFeedback(
        'online',
        `Started embedding ${enqueued.toLocaleString()} file(s)…`,
      )
      await refreshIndexStatus()
    } catch (err) {
      setCorpusFeedback('error', err?.message || String(err))
    } finally {
      setBusyKey(null)
    }
  }

  async function pauseEmbeddings() {
    if (!window.api?.embeddingsPause) return
    setBusyKey('embeddings-pause')
    try {
      const result = await window.api.embeddingsPause()
      if (!result.ok) {
        setCorpusFeedback('error', result.error || 'Pause failed')
        return
      }
      setIndexStatus((prev) =>
        prev
          ? {
              ...prev,
              embed_paused: true,
              embed_queue_depth: result.data?.queue_depth ?? prev.embed_queue_depth,
            }
          : prev,
      )
      setCorpusFeedback('online', 'Paused.')
      await refreshIndexStatus()
    } catch (err) {
      setCorpusFeedback('error', err?.message || String(err))
    } finally {
      setBusyKey(null)
    }
  }

  async function resumeEmbeddings() {
    if (!window.api?.embeddingsResume) return
    setBusyKey('embeddings-resume')
    try {
      const result = await window.api.embeddingsResume()
      if (!result.ok) {
        setCorpusFeedback('error', result.error || 'Resume failed')
        return
      }
      setIndexStatus((prev) =>
        prev
          ? {
              ...prev,
              embed_paused: false,
              embed_queue_depth: result.data?.queue_depth ?? prev.embed_queue_depth,
            }
          : prev,
      )
      setCorpusFeedback('online', 'Resumed.')
      await refreshIndexStatus()
    } catch (err) {
      setCorpusFeedback('error', err?.message || String(err))
    } finally {
      setBusyKey(null)
    }
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
  const vectorStore = payload?.capabilities?.vector_store
  const models = payload?.capabilities?.models
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
            {indexStatus?.embedding_chunk_count != null
              ? ` · ${indexStatus.embedding_chunk_count.toLocaleString()} embedding chunk${
                  indexStatus.embedding_chunk_count === 1 ? '' : 's'
                }`
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

          {indexStatus?.watched_roots > 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {indexStatus.watch_paused
                ? 'Live watching paused'
                : indexStatus.watching
                  ? `Live watching ${indexStatus.watched_roots} folder${indexStatus.watched_roots === 1 ? '' : 's'}`
                  : `Watchers attached (${indexStatus.watched_roots})`}
              {indexStatus.queue_depth > 0
                ? ` · ${indexStatus.queue_depth} pending`
                : ''}
            </Typography>
          ) : null}

          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Only folders you add are indexed. Whole-PC / whole-disk crawling is out
            of scope for defaults. New, deleted, and renamed files in those folders
            update the index automatically.
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
                <p className={`status status-${vectorStoreTone(vectorStore)}`}>
                  <span className="status-label">Vector store:</span>{' '}
                  {vectorStoreLabel(vectorStore)}
                  {typeof vectorStore?.chunk_count === 'number'
                    ? ` · ${vectorStore.chunk_count.toLocaleString()} chunk${
                        vectorStore.chunk_count === 1 ? '' : 's'
                      }`
                    : ''}
                </p>
                <p className={`status status-${embeddingTone(models)}`}>
                  <span className="status-label">Embedding model:</span>{' '}
                  {embeddingLabel(models)}
                </p>
                <p className={`status status-${gpuTone(gpu)}`}>
                  <span className="status-label">GPU:</span> {gpuLabel(gpu)}
                </p>
                <p
                  className={`status status-${
                    indexStatus?.embed_paused ? 'loading' : 'online'
                  }`}
                >
                  <span className="status-label">Embed queue:</span>{' '}
                  {indexStatus?.embed_paused
                    ? 'Paused'
                    : embedQueueDepth > 0
                      ? 'Running'
                      : 'Idle'}
                  {indexStatus?.embed_queue_depth != null
                    ? ` · ${indexStatus.embed_queue_depth} queued`
                    : ''}
                  {(indexStatus?.embed_pending_files ?? 0) > 0
                    ? ` · ${indexStatus.embed_pending_files} pending`
                    : ''}
                  {indexStatus?.embedding_chunk_count != null
                    ? ` · ${indexStatus.embedding_chunk_count} chunks`
                    : ''}
                  {indexStatus?.embed_completed != null
                    ? ` · ${indexStatus.embed_completed} done`
                    : ''}
                  {(indexStatus?.embed_failed ?? 0) > 0
                    ? ` · ${indexStatus.embed_failed} failed`
                    : ''}
                  {embedQueueDepth > 0 && !indexStatus?.embed_paused
                    ? ' · updating…'
                    : ''}
                </p>
                {(indexStatus?.embedded_files?.length ?? 0) > 0 ? (
                  <Typography
                    variant="body2"
                    sx={{ mb: 1.25, color: colors.textPrimary, lineHeight: 1.45 }}
                  >
                    <span className="status-label">Embedded:</span>{' '}
                    {indexStatus.embedded_files
                      .map((f) => `${f.name} (${f.chunks})`)
                      .join(' · ')}
                  </Typography>
                ) : null}
                {indexStatus?.embed_last_error ? (
                  <Typography variant="body2" color="error" sx={{ mb: 1 }}>
                    Last error: {indexStatus.embed_last_error}
                  </Typography>
                ) : null}

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
                    <dd>{gpuLabel(gpu)}</dd>
                  </div>
                  <div>
                    <dt>Embed dim</dt>
                    <dd>{vectorStore?.dimension ?? 768}</dd>
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

            <Box
              sx={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 1,
                alignItems: 'center',
                mb: 1,
              }}
            >
              <Button
                variant="contained"
                color="primary"
                onClick={checkSystemStatus}
                disabled={phase === 'loading'}
              >
                Check
              </Button>
              {(indexStatus?.embed_pending_files ?? 0) > 0 ? (
                <Button
                  variant="contained"
                  color="primary"
                  onClick={startEmbedding}
                  disabled={busy || phase === 'loading'}
                >
                  {busyKey === 'embeddings-start'
                    ? 'Starting…'
                    : `Start embedding (${indexStatus.embed_pending_files})`}
                </Button>
              ) : null}
              {indexStatus?.embed_paused ||
              (indexStatus?.embed_queue_depth ?? 0) > 0 ? (
                <Button
                  variant={indexStatus?.embed_paused ? 'contained' : 'outlined'}
                  color="primary"
                  onClick={
                    indexStatus?.embed_paused
                      ? resumeEmbeddings
                      : pauseEmbeddings
                  }
                  disabled={busy || phase === 'loading'}
                >
                  {indexStatus?.embed_paused ? 'Resume' : 'Pause'}
                </Button>
              ) : null}
            </Box>

            <Accordion
              disableGutters
              elevation={0}
              expanded={advancedOpen}
              onChange={(_event, expanded) => setAdvancedOpen(expanded)}
              sx={{
                backgroundColor: 'transparent',
                border: `1px solid ${colors.border}`,
                '&:before': { display: 'none' },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandIcon />}
                sx={{
                  minHeight: 40,
                  px: 1,
                  '& .MuiAccordionSummary-content': { my: 0.75 },
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ fontWeight: 600, color: colors.textSecondary }}
                >
                  Advanced
                </Typography>
              </AccordionSummary>
              <AccordionDetails sx={{ px: 1, pt: 0, pb: 1 }}>
                <Button
                  variant="outlined"
                  color="primary"
                  size="small"
                  onClick={verifyVectorStore}
                  disabled={busy || phase === 'loading'}
                >
                  {busyKey === 'embeddings-smoke'
                    ? 'Verifying…'
                    : 'Verify vector store'}
                </Button>
              </AccordionDetails>
            </Accordion>
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
