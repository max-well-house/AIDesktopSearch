import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import SearchBar from './SearchBar'
import MosaicCanvas from './MosaicCanvas'
import EmptyState from './EmptyState'
import ResultsList from './ResultsList'
import Footer from './Footer'
import { colors } from '../../theme'

const SEARCH_DEBOUNCE_MS = 200

/**
 * Permanent launcher shell. Structure is stable for v1:
 * Search → (Mosaic idle | Results slot) → Footer.
 */
export default function LauncherWindow() {
  const inputRef = useRef(null)
  const [query, setQuery] = useState('')
  const [searchKey, setSearchKey] = useState(0)
  const [indexedLabel, setIndexedLabel] = useState('—')
  const [hits, setHits] = useState([])
  const [status, setStatus] = useState('idle')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const isIdle = query.trim().length === 0

  useEffect(() => {
    let cancelled = false
    async function loadIndexStatus() {
      if (!window.api?.getIndexStatus) return
      const result = await window.api.getIndexStatus()
      if (cancelled || !result.ok) return
      const count = result.data?.file_count ?? 0
      if (count === 0) setIndexedLabel('0 files')
      else if (count === 1) setIndexedLabel('1 file')
      else setIndexedLabel(`${count.toLocaleString()} files`)
    }
    void loadIndexStatus()
    return () => {
      cancelled = true
    }
  }, [])

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
      if (!window.api?.search) {
        if (!cancelled) {
          setHits([])
          setStatus('error')
        }
        return
      }
      const result = await window.api.search(q)
      if (cancelled) return
      if (!result.ok) {
        setHits([])
        setStatus('error')
        setSelectedIndex(0)
        return
      }
      const next = result.data?.results ?? []
      setHits(next)
      setStatus('ready')
      setSelectedIndex(0)
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      cancelled = true
      clearTimeout(timer)
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

  function handleSearchKeyDown(event) {
    if (isIdle || hits.length === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setSelectedIndex((i) => Math.min(i + 1, hits.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setSelectedIndex((i) => Math.max(i - 1, 0))
    }
    // Enter / click open → #44
  }

  const footerStatus = [
    { label: 'Indexed', value: indexedLabel },
    { label: 'Semantic Search', value: 'Disabled' },
    { label: 'AI', value: 'Offline' },
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
    resultsBody = <ResultsList hits={hits} selectedIndex={selectedIndex} />
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
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

      <Footer status={footerStatus} />
    </Box>
  )
}
