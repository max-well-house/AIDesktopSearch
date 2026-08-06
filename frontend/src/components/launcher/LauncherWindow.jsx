import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import Box from '@mui/material/Box'
import IconButton from '@mui/material/IconButton'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import SearchBar from './SearchBar'
import MosaicCanvas from './MosaicCanvas'
import EmptyState from './EmptyState'
import ResultsList, { resultOptionId } from './ResultsList'
import Footer from './Footer'
import StatusBanner from './StatusBanner'
import AppMark from '../brand/AppMark'
import { colors } from '../../theme'
import appConfig from '@app-config'
import { DEFAULT_LAUNCHER_SHORTCUT_LABEL } from '../../shortcutAccelerator'

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
  return `${data.file_count ?? 0}|${data.last_indexed_at ?? ''}|${data.queue_depth ?? 0}|${data.embedding_chunk_count ?? 0}|${data.semantic_query_ready ? 1 : 0}|${data.chat_ready ? 1 : 0}|${data.embed_queue_depth ?? 0}|${data.embed_paused ? 1 : 0}`
}

/**
 * Permanent launcher shell. Structure is stable for v1:
 * Search → (Mosaic idle | Results slot) → Footer.
 */
export default function LauncherWindow({ onOpenSettings, settingsOpen = false }) {
  const inputRef = useRef(null)
  const hitsRef = useRef([])
  const selectedIndexRef = useRef(0)
  const indexFpRef = useRef('')
  const preferSemanticRef = useRef(true)
  const settingsOpenRef = useRef(false)
  const [query, setQuery] = useState('')
  const [searchKey, setSearchKey] = useState(0)
  const [indexedLabel, setIndexedLabel] = useState('—')
  const [semanticFooter, setSemanticFooter] = useState({
    value: 'Disabled',
    tone: 'off',
    title: 'Semantic search is not ready',
  })
  const [aiFooter, setAiFooter] = useState({
    value: 'Offline',
    tone: 'degraded',
    title: 'Local AI needs Ollama and a chat model (llama3.2:3b)',
  })
  const [preferSemantic, setPreferSemantic] = useState(true)
  const [indexSnapshot, setIndexSnapshot] = useState(null)
  const [hits, setHits] = useState([])
  const [status, setStatus] = useState('idle')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [launcherShortcut, setLauncherShortcut] = useState(DEFAULT_LAUNCHER_SHORTCUT_LABEL)
  const [banner, setBanner] = useState(null)
  const [addingFolder, setAddingFolder] = useState(false)
  const dismissedBannerIdsRef = useRef(new Set())
  const isIdle = query.trim().length === 0
  // Status unknown → keep search-first copy; only flip when we know root_count is 0 (#146).
  const zeroRoots =
    indexSnapshot != null &&
    (indexSnapshot.root_count ?? indexSnapshot.roots?.length ?? 0) === 0

  hitsRef.current = hits
  selectedIndexRef.current = selectedIndex
  preferSemanticRef.current = preferSemantic
  settingsOpenRef.current = settingsOpen

  function showBanner(id, message, tone = 'error') {
    if (!message) return
    if (dismissedBannerIdsRef.current.has(id)) return
    setBanner({ id, message, tone })
  }

  function dismissBanner() {
    if (banner?.id) {
      dismissedBannerIdsRef.current.add(banner.id)
    }
    setBanner(null)
  }

  function clearBannerDismissal(id) {
    dismissedBannerIdsRef.current.delete(id)
  }

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

  function deriveAiFooter(data) {
    if (data?.chat_ready === true) {
      return {
        value: 'Ready',
        tone: 'on',
        title: 'Local chat model ready (llama3.2:3b) — answers ship with RAG in v1.1',
      }
    }
    return {
      value: 'Offline',
      tone: 'degraded',
      title:
        'Local AI needs Ollama running with llama3.2:3b — classic and semantic search still work',
    }
  }

  function applyIndexStatus(data) {
    if (!data) return
    const count = data.file_count ?? 0
    const lastIndexedAt = data.last_indexed_at ?? null
    setIndexedLabel(formatIndexedLabel(count, lastIndexedAt))
    setIndexSnapshot(data)
    setSemanticFooter(deriveSemanticFooter(data, preferSemanticRef.current))
    setAiFooter(deriveAiFooter(data))
    indexFpRef.current = indexFingerprint(data)

    // Index / embed attention path (#119) — one warning, dismissible for the session.
    if (data.embed_last_error) {
      showBanner(
        'index-embed-error',
        `Embedding needs attention: ${String(data.embed_last_error).slice(0, 120)}`,
        'warning',
      )
    } else if (data.watch_paused) {
      clearBannerDismissal('index-embed-error')
      showBanner(
        'index-watch-paused',
        'Live watching is paused — the index may fall behind until you resume in Settings.',
        'warning',
      )
    } else {
      clearBannerDismissal('index-embed-error')
      clearBannerDismissal('index-watch-paused')
      setBanner((prev) =>
        prev?.id === 'index-embed-error' || prev?.id === 'index-watch-paused'
          ? null
          : prev,
      )
    }
  }

  async function runSearch(q, { resetSelection, isCancelled } = {}) {
    if (!window.api?.search) {
      if (isCancelled?.()) return
      setHits([])
      setStatus('error')
      clearBannerDismissal('search-error')
      showBanner('search-error', 'Search unavailable — backend did not respond.', 'error')
      return
    }
    const result = await window.api.search(q, undefined, 'auto')
    if (isCancelled?.()) return
    if (!result.ok) {
      setHits([])
      setStatus('error')
      setSelectedIndex(0)
      clearBannerDismissal('search-error')
      showBanner(
        'search-error',
        result.error || 'Search unavailable — try again in a moment.',
        'error',
      )
      return
    }
    clearBannerDismissal('search-error')
    setBanner((prev) => (prev?.id === 'search-error' ? null : prev))
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

  async function addFolderFromIdle() {
    if (!window.api?.pickFolder || !window.api?.scanFolder) {
      showBanner(
        'add-folder-error',
        'Folder picker unavailable — open Settings to add a folder.',
        'error',
      )
      return
    }

    const picked = await window.api.pickFolder()
    if (picked.canceled || !picked.ok || !picked.path) return

    setAddingFolder(true)
    try {
      const result = await window.api.scanFolder(picked.path)
      if (!result.ok) {
        showBanner(
          'add-folder-error',
          result.error || 'Could not add that folder — try again from Settings.',
          'error',
        )
        return
      }
      clearBannerDismissal('add-folder-error')
      setBanner((prev) => (prev?.id === 'add-folder-error' ? null : prev))
      const statusResult = await window.api.getIndexStatus()
      if (statusResult.ok) applyIndexStatus(statusResult.data)
    } catch (err) {
      showBanner(
        'add-folder-error',
        err?.message || 'Could not add that folder — try again from Settings.',
        'error',
      )
    } finally {
      setAddingFolder(false)
    }
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
    async function loadShortcut() {
      if (!window.api?.getLauncherShortcut) return
      const result = await window.api.getLauncherShortcut()
      if (cancelled || !result?.ok) return
      setLauncherShortcut(
        result.accelerator || result.preferred || DEFAULT_LAUNCHER_SHORTCUT_LABEL,
      )
    }
    void loadShortcut()
    const unsubShortcut = window.api?.onLauncherShortcutChanged?.((accel) => {
      setLauncherShortcut(accel || DEFAULT_LAUNCHER_SHORTCUT_LABEL)
    })
    return () => {
      cancelled = true
      clearInterval(idlePoll)
      unsubPrefer?.()
      unsubShortcut?.()
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
      })
    }

    const unsubDismiss = window.api?.onDismiss?.(() => {
      // Settings drawer owns the first Esc; keep query until drawer closes.
      if (settingsOpenRef.current) return
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
    clearBannerDismissal('open-error')
    setBanner((prev) => (prev?.id === 'open-error' ? null : prev))

    if (!window.api?.openPath) {
      showBanner('open-error', 'Open unavailable', 'error')
      return
    }

    const result = await window.api.openPath(hit.path)
    if (!result.ok) {
      showBanner('open-error', result.error || 'Could not open file', 'error')
      return
    }

    flushSync(() => {
      setQuery('')
      setSearchKey((key) => key + 1)
      setHits([])
      setStatus('idle')
      setSelectedIndex(0)
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

  const toggleKeys = launcherShortcut || DEFAULT_LAUNCHER_SHORTCUT_LABEL
  const footerShortcuts = isIdle
    ? [
        { keys: toggleKeys, action: 'Toggle' },
        { keys: 'Esc', action: 'Dismiss' },
      ]
    : [
        { keys: '↑↓', action: 'Select' },
        { keys: 'Enter', action: 'Open' },
        { keys: toggleKeys, action: 'Toggle' },
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
      value: aiFooter.value,
      tone: aiFooter.tone,
      title: aiFooter.title,
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
      <ResultsList
        hits={hits}
        selectedIndex={selectedIndex}
        onActivate={openHit}
      />
    )
  }

  const statusBanner = banner ? (
    <StatusBanner
      message={banner.message}
      tone={banner.tone}
      onDismiss={dismissBanner}
    />
  ) : null

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
        <Box
          sx={{
            maxWidth: 720,
            mx: 'auto',
            display: 'flex',
            alignItems: 'center',
            gap: 1.25,
          }}
        >
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <SearchBar
              key={searchKey}
              ref={inputRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onClear={() => setQuery('')}
              onKeyDown={handleSearchKeyDown}
              activeDescendantId={
                hits.length > 0 ? resultOptionId(selectedIndex) : undefined
              }
            />
          </Box>
          {onOpenSettings ? (
            <Tooltip
              title="Settings"
              placement="bottom"
              slotProps={{
                tooltip: {
                  sx: {
                    bgcolor: colors.surface,
                    color: colors.textPrimary,
                    border: `1px solid ${colors.border}`,
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    px: 1,
                    py: 0.5,
                  },
                },
              }}
            >
              <IconButton
                aria-label={`${appConfig.name} — open Settings`}
                onClick={onOpenSettings}
                size="small"
                sx={{
                  WebkitAppRegion: 'no-drag',
                  flexShrink: 0,
                  width: 48,
                  height: 48,
                  p: 0.75,
                  borderRadius: 2,
                  border: `1px solid ${colors.border}`,
                  bgcolor: colors.surface,
                  transition:
                    'background-color 160ms ease, border-color 160ms ease, transform 160ms ease',
                  '&:hover': {
                    bgcolor: colors.hover,
                    borderColor: colors.accentTeal,
                    transform: 'scale(1.03)',
                  },
                }}
              >
                <AppMark size={32} />
              </IconButton>
            </Tooltip>
          ) : null}
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
          {isIdle ? (
            <EmptyState
              zeroRoots={zeroRoots}
              addingFolder={addingFolder}
              onAddFolder={() => void addFolderFromIdle()}
              onOpenSettings={onOpenSettings}
            />
          ) : null}
        </Box>

        {isIdle ? (
          <Box
            sx={{
              position: 'relative',
              zIndex: 3,
              px: { xs: 2, sm: 3 },
              pt: 1,
            }}
          >
            <Box sx={{ maxWidth: 720, mx: 'auto' }}>{statusBanner}</Box>
          </Box>
        ) : null}

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
            <Box sx={{ maxWidth: 720, mx: 'auto', pt: 1 }}>
              {statusBanner}
              {resultsBody}
            </Box>
          </Box>
        ) : null}
      </Box>

      <Footer status={footerStatus} shortcuts={footerShortcuts} />
    </Box>
  )
}
