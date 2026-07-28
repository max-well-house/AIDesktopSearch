import { useEffect, useState } from 'react'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import Drawer from '@mui/material/Drawer'
import Box from '@mui/material/Box'
import theme, { colors } from './theme'
import { LauncherWindow } from './components/launcher'
import Settings from './components/Settings'

const TITLEBAR_HEIGHT = 'env(titlebar-area-height, 32px)'

export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false)

  // Escape while Settings is open: close the drawer only (second Esc dismisses).
  useEffect(() => {
    if (!settingsOpen) return undefined
    return window.api?.onDismiss?.(() => {
      setSettingsOpen(false)
    })
  }, [settingsOpen])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {/* Drag strip under dark titleBarOverlay — stays active with drawer open. */}
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
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          pt: TITLEBAR_HEIGHT,
          boxSizing: 'border-box',
        }}
      >
        <Box sx={{ flex: 1, minHeight: 0, position: 'relative' }}>
          <LauncherWindow
            onOpenSettings={() => setSettingsOpen(true)}
            settingsOpen={settingsOpen}
          />
        </Box>
      </Box>

      <Drawer
        anchor="right"
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        ModalProps={{
          disableScrollLock: true,
        }}
        slotProps={{
          backdrop: {
            sx: {
              backgroundColor: 'rgba(0, 0, 0, 0.55)',
            },
          },
        }}
        PaperProps={{
          sx: {
            width: { xs: '100%', sm: '75%' },
            maxWidth: 640,
            // Solid panel — frost was muddy; keep drawer, skip glass.
            bgcolor: colors.drawer,
            backgroundImage: 'none',
            borderLeft: `1px solid ${colors.border}`,
            boxShadow: '-12px 0 40px rgba(0, 0, 0, 0.65)',
            WebkitAppRegion: 'no-drag',
          },
        }}
      >
        <Settings onBack={() => setSettingsOpen(false)} />
      </Drawer>
    </ThemeProvider>
  )
}
