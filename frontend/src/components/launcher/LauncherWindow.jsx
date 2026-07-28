import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import SearchBar from './SearchBar'
import MosaicCanvas from './MosaicCanvas'
import EmptyState from './EmptyState'
import ResultsList, { resultOptionId } from './ResultsList'
import Footer from './Footer'
import { colors } from '../../theme'

const SEARCH_DEBOUNCE_MS = 200
/** Light status poll while a query is open — refresh hits when the index fingerprint changes (v0.4). */
const INDEX_POLL_MS = 1500

/** Footer Indexed value: `N files` or `N files (7/23/2026)` when last_indexed_at is known (#115). */
function formatIndexedLabel(count, lastIndexedAt) {
  let files
  if (count === 0) files = '0 files'
  else if (count === 1) files = '1 file'
  else files = `${Number(count).toLocaleString()} files`

  if (!lastIndexedAt) return files
  const date = new Date(lastIndexedAt)
  if (Number.isNaN(date.getTime())) return files
  return `${files} (${date.toLocaleDateString()})`
}

/** Cheap signal that SQLite changed — not a hot search loop (#52-friendly). */
function indexFingerprint(data) {
  if (!data) return ''
  return `${data.file_count ?? 0}|${data.last_indexed_at ?? ''}|${data.queue_depth ?? 0}|${data.embedding_chunk_count ?? 0}|${data.semantic_query_ready ? 1 : 0}|${data.embed_queue_depth ?? 0}|${data.embed_paused ? 1 : 0}`
}

/**
 * Permanent launcher shell. Structure is stable for v1:
 * Search → (Mosaic idle | Results slot) → Footer.
 */
export default function LauncherWindow() {
  const inputRef = useRef(null)
  const hitsRef = useRef([])
  const selectedIndexRef = useRef(0)
  const indexFpRef = useRef('')
  const preferSemanticRef = useRef(true)
  const [query, setQuery] = useState('')
  const [searchKey, setSearchKey] = useState(0)
  const [indexedLabel, setIndexedLabel] = useState('—')
  const [semanticFooter, setSemanticFooter] = useState({
    value: 'Disabled',
    tone: 'off',
    title: 'Semantic search is not ready',
  })
  const [preferSemantic, setPreferSemantic] = useState(true)
  const [indexSnapshot, setIndexSnapshot] = useState(null)
  const [hits, setHits] = useState([])
  const [status, setStatus] = useState('idle')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [openError, setOpenError] = useState(null)
  const isIdle = query.trim().length === 0

  hitsRef.current = hits
  selectedIndexRef.current = selectedIndex
  preferSemanticRef.current = preferSemantic

  function deriveSemanticFooter(data, prefer) {
    if (!prefer) {
      return {
        value: 'Off',
        tone: 'off',
        title: 'Semantic search is turned off in Settings',
      }
    }
    const ready =
      data?.semantic_query_ready === true ||
      (data?.semantic_query_ready == null &&
        (data?.embedding_chunk_count ?? 0) > 0 &&
        data?.vector_store_available === true)
    if (ready) {
      return {
        value: 'Available',
        tone: 'on',
        title: 'Meaning search is ready (Ollama + embeddings)',
      }
    }
    const queue = data?.embed_queue_depth ?? 0
    if (queue > 0 || data?.embed_paused) {
      return {
        value: data?.embed_paused ? 'Paused' : `Embedding… ${queue}`,
        tone: 'degraded',
        title: data?.embed_paused
          ? 'Embedding paused — resume in Settings'
          : 'Embeddings are still building; meaning search will turn green when ready',
      }
    }
    return {
      value: 'Unavailable',
      tone: 'degraded',
      title:
        'Preferred on, but not ready — need Ollama, nomic-embed-text, and embedded files',
    }
  }

  function applyIndexStatus(data) {
    if (!data) return
    const count = data.file_count ?? 0
    const lastIndexedAt = data.last_indexed_at ?? null
    setIndexedLabel(formatIndexedLabel(count, lastIndexedAt))
    setIndexSnapshot(data)
    setSemanticFooter(deriveSemanticFooter(data, preferSemanticRef.current))
    indexFpRef.current = indexFingerprint(data)
  }

  async function runSearch(q, { resetSelection, isCancelled } = {}) {
    if (!window.api?.search) {
      if (isCancelled?.()) return
      setHits([])
      setStatus('error')
      return
    }
    const result = await window.api.search(q, undefined, 'auto')
    if (isCancelled?.()) return
    if (!result.ok) {
      setHits([])
      setStatus('error')
      setSelectedIndex(0)
      return
    }
    const next = result.data?.results ?? []
    if (resetSelection) {
      setHits(next)
      setSelectedIndex(0)
    } else {
      const prevPath = hitsRef.current[selectedIndexRef.current]?.path
      const keep = prevPath ? next.findIndex((h) => h.path === prevPath) : -1
      setHits(next)
      setSelectedIndex(keep >= 0 ? keep : 0)
    }
    setStatus('ready')
  }

  useEffect(() => {
    let cancelled = false
    async function loadIndexStatus() {
      if (!window.api?.getIndexStatus) return
      const result = await window.api.getIndexStatus()
      if (cancelled || !result.ok) return
      applyIndexStatus(result.data)
    }
    async function loadPreferSemantic() {
      if (!window.api?.getPreferSemanticSearch) return
      const result = await window.api.getPreferSemanticSearch()
      if (cancelled || !result?.ok) return
      setPreferSemantic(Boolean(result.enabled))
    }
    void loadIndexStatus()
    void loadPreferSemantic()
    // Light footer refresh while idle (embedding → ready).
    const idlePoll = setInterval(() => {
      void loadIndexStatus()
    }, 3000)
    const unsubPrefer = window.api?.onPreferSemanticChanged?.((enabled) => {
      setPreferSemantic(enabled)
    })
    return () => {
      cancelled = true
      clearInterval(idlePoll)
      unsubPrefer?.()
    }
  }, [])

  // Re-derive footer when prefer toggles after status is known.
  useEffect(() => {
    if (!indexSnapshot) return
    setSemanticFooter(deriveSemanticFooter(indexSnapshot, preferSemantic))
  }, [preferSemantic, indexSnapshot])

  // Debounced classic filename search (#43).
  useEffect(() => {
    const q = query.trim()
    setOpenError(null)
    if (!q) {
      setHits([])
      setStatus('idle')
      setSelectedIndex(0)
      return undefined
    }

    let cancelled = false
    setStatus((prev) => (prev === 'ready' ? prev : 'loading'))

    const timer = setTimeout(async () => {
      await runSearch(q, {
        resetSelection: true,
        isCancelled: () => cancelled,
      })
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query])

  // While a query is open, poll index status lightly; re-search only when fingerprint changes.
  // Does not fight #52: watcher stays debounced; UI only re-queries after SQLite actually moved.
  useEffect(() => {
    const q = query.trim()
    if (!q || !window.api?.getIndexStatus) return undefined

    let cancelled = false
    const tick = async () => {
      const statusResult = await window.api.getIndexStatus()
      if (cancelled || !statusResult.ok) return
      const nextFp = indexFingerprint(statusResult.data)
      if (nextFp === indexFpRef.current) return
      applyIndexStatus(statusResult.data)
      await runSearch(q, {
        resetSelection: false,
        isCancelled: () => cancelled,
      })
    }

    const id = setInterval(() => {
      void tick()
    }, INDEX_POLL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [query])

  useEffect(() => {
    const afterPaint = (fn) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(fn)
      })
    }

    const clearSearch = () => {
      flushSync(() => {
        setQuery('')
        setSearchKey((key) => key + 1)
        setHits([])
        setStatus('idle')
        setSelectedIndex(0)
        setOpenError(null)
      })
    }

    const unsubDismiss = window.api?.onDismiss?.(() => {
      clearSearch()
      // Let Chromium paint the empty field before hide (avoids caching a stale frame).
      afterPaint(() => {
        void window.api?.hideLauncher?.()
      })
    })

    const unsubScrub = window.api?.onScrubBeforeShow?.(() => {
      clearSearch()
      afterPaint(() => {
        inputRef.current?.focus?.()
        void window.api?.notifyShowPrepared?.()
      })
    })

    return () => {
      unsubDismiss?.()
      unsubScrub?.()
    }
  }, [])

  async function openHit(hit, index) {
    if (!hit?.path) return
    if (typeof index === 'number') setSelectedIndex(index)
    setOpenError(null)

    if (!window.api?.openPath) {
      setOpenError('Open unavailable')
      return
    }

    const result = await window.api.openPath(hit.path)
    if (!result.ok) {
      setOpenError(result.error || 'Could not open file')
      return
    }

    flushSync(() => {
      setQuery('')
      setSearchKey((key) => key + 1)
      setHits([])
      setStatus('idle')
      setSelectedIndex(0)
      setOpenError(null)
    })
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        void window.api?.hideLauncher?.({ scrubNextShow: true })
      })
    })
  }

  function handleSearchKeyDown(event) {
    if (isIdle || hits.length === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setSelectedIndex((i) => (i + 1) % hits.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setSelectedIndex((i) => (i - 1 + hits.length) % hits.length)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const hit = hits[selectedIndex]
      if (hit) void openHit(hit, selectedIndex)
    }
  }

  const footerShortcuts = isIdle
    ? [
        { keys: 'Alt+Space', action: 'Toggle' },
        { keys: 'Esc', action: 'Dismiss' },
      ]
    : [
        { keys: '↑↓', action: 'Select' },
        { keys: 'Enter', action: 'Open' },
        { keys: 'Alt+Space', action: 'Toggle' },
        { keys: 'Esc', action: 'Dismiss' },
      ]

  const footerStatus = [
    { label: 'Indexed', value: indexedLabel },
    {
      label: 'Semantic Search',
      value: semanticFooter.value,
      tone: semanticFooter.tone,
      title: semanticFooter.title,
    },
    {
      label: 'AI',
      value: 'Offline',
      tone: 'degraded',
      title: 'Local AI answers ship in v1.1 — chat is not available yet',
    },
  ]

  let resultsBody = null
  if (status === 'error') {
    resultsBody = (
      <Typography variant="body2" sx={{ color: colors.textSecondary, pt: 1, px: 0.5 }}>
        Search unavailable
      </Typography>
    )
  } else if (status === 'loading' && hits.length === 0) {
    resultsBody = (
      <Typography variant="body2" sx={{ color: colors.textSecondary, pt: 1, px: 0.5 }}>
        Searching…
      </Typography>
    )
  } else if (status === 'ready' && hits.length === 0) {
    resultsBody = (
      <Typography variant="body2" sx={{ color: colors.textSecondary, pt: 1, px: 0.5 }}>
        No files match “{query.trim()}”
      </Typography>
    )
  } else if (hits.length > 0) {
    resultsBody = (
      <>
        {openError ? (
          <Typography
            variant="body2"
            sx={{ color: colors.textSecondary, px: 0.5, pb: 1 }}
            role="alert"
          >
            {openError}
          </Typography>
        ) : null}
        <ResultsList
          hits={hits}
          selectedIndex={selectedIndex}
          onActivate={openHit}
        />
      </>
    )
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        bgcolor: colors.background,
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          flexShrink: 0,
          px: { xs: 2, sm: 3 },
          pt: { xs: 2.5, sm: 3 },
          pb: 2,
        }}
      >
        <Box sx={{ maxWidth: 720, mx: 'auto' }}>
          <SearchBar
            key={searchKey}
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleSearchKeyDown}
            activeDescendantId={
              hits.length > 0 ? resultOptionId(selectedIndex) : undefined
            }
          />
        </Box>
      </Box>

      <Box
        sx={{
          position: 'relative',
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            opacity: isIdle ? 1 : 0,
            transition: 'opacity 280ms ease',
          }}
        >
          <MosaicCanvas active={isIdle} />
        </Box>

        <Box
          sx={{
            position: 'relative',
            zIndex: 1,
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            px: 2,
            opacity: isIdle ? 1 : 0.35,
            transition: 'opacity 220ms ease',
            pointerEvents: isIdle ? 'auto' : 'none',
          }}
        >
          {isIdle ? <EmptyState /> : null}
        </Box>

        {!isIdle ? (
          <Box
            sx={{
              position: 'absolute',
              inset: 0,
              zIndex: 2,
              px: { xs: 2, sm: 3 },
              pb: 1,
              overflow: 'auto',
            }}
            aria-live="polite"
          >
            <Box sx={{ maxWidth: 720, mx: 'auto', pt: 1 }}>{resultsBody}</Box>
          </Box>
        ) : null}
      </Box>

      <Footer status={footerStatus} shortcuts={footerShortcuts} />
    </Box>
  )
}
