import { useEffect, useState } from 'react'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import IconButton from '@mui/material/IconButton'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import theme, { colors } from './theme'
import { LauncherWindow } from './components/launcher'
import Settings from './components/Settings'
import AppMark from './components/brand/AppMark'
import appConfig from '@app-config'

const TITLEBAR_HEIGHT = 'env(titlebar-area-height, 32px)'

export default function App() {
  const [view, setView] = useState('launcher')

  // Escape on Settings: return to launcher, then hide (so reopen is search-first).
  useEffect(() => {
    if (view !== 'settings') return undefined
    return window.api?.onDismiss?.(() => {
      setView('launcher')
      window.api?.hideLauncher?.({ scrubNextShow: true })
    })
  }, [view])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {/* Drag strip under dark titleBarOverlay (Windows caption buttons stay native). */}
      <Box
        aria-hidden
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          height: TITLEBAR_HEIGHT,
          width: 'env(titlebar-area-width, 100%)',
          WebkitAppRegion: 'drag',
          zIndex: 2000,
        }}
      />
      {/* Keep launcher mounted so Settings round-trip preserves the query (#83 feel). */}
      <Box
        sx={{
          display: view === 'launcher' ? 'flex' : 'none',
          flexDirection: 'column',
          position: 'relative',
          height: '100vh',
          pt: TITLEBAR_HEIGHT,
          boxSizing: 'border-box',
        }}
      >
        <Box sx={{ flex: 1, minHeight: 0, position: 'relative' }}>
          <LauncherWindow />
          <IconButton
            aria-label={`${appConfig.name} — open Settings`}
            onClick={() => setView('settings')}
            size="small"
            sx={{
              position: 'absolute',
              top: 8,
              right: 12,
              zIndex: 3,
              WebkitAppRegion: 'no-drag',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 0.25,
              px: 0.75,
              py: 0.5,
              borderRadius: 1.5,
              border: `1px solid ${colors.border}`,
              bgcolor: colors.surface,
              opacity: 0.96,
              transition: 'opacity 160ms ease, background-color 160ms ease, border-color 160ms ease',
              '&:hover': {
                opacity: 1,
                bgcolor: colors.hover,
                borderColor: colors.accentTeal,
              },
            }}
          >
            <AppMark size={28} />
            <Typography
              component="span"
              variant="caption"
              sx={{
                color: colors.textSecondary,
                fontSize: '0.65rem',
                fontWeight: 600,
                letterSpacing: '0.04em',
                lineHeight: 1,
                textTransform: 'uppercase',
              }}
            >
              Settings
            </Typography>
          </IconButton>
        </Box>
      </Box>
      {view === 'settings' ? (
        <Box
          sx={{
            height: '100vh',
            pt: TITLEBAR_HEIGHT,
            boxSizing: 'border-box',
            WebkitAppRegion: 'no-drag',
          }}
        >
          <Settings onBack={() => setView('launcher')} />
        </Box>
      ) : null}
    </ThemeProvider>
  )
}
