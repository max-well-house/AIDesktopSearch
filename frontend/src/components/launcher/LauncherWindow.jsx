import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import Box from '@mui/material/Box'
import SearchBar from './SearchBar'
import MosaicCanvas from './MosaicCanvas'
import EmptyState from './EmptyState'
import Footer from './Footer'
import { colors } from '../../theme'

/**
 * Permanent launcher shell. Structure is stable for v1:
 * Search → (Mosaic idle | Results slot) → Footer.
 * Search logic / results / preview land later without redesigning this tree.
 */
export default function LauncherWindow() {
  const inputRef = useRef(null)
  const [query, setQuery] = useState('')
  const [searchKey, setSearchKey] = useState(0)
  const [indexedLabel, setIndexedLabel] = useState('—')
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

  const footerStatus = [
    { label: 'Indexed', value: indexedLabel },
    { label: 'Semantic Search', value: 'Disabled' },
    { label: 'AI', value: 'Offline' },
  ]

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

        {/* Results slot — list / preview / AI / related / actions grow here later */}
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
            <Box
              sx={{
                maxWidth: 720,
                mx: 'auto',
                pt: 1,
                color: colors.textSecondary,
                typography: 'body2',
              }}
            >
              {/* Quiet placeholder until search lands — intentional, not "No Results" */}
            </Box>
          </Box>
        ) : null}
      </Box>

      <Footer status={footerStatus} />
    </Box>
  )
}
