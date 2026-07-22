import { useState } from 'react'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import IconButton from '@mui/material/IconButton'
import Box from '@mui/material/Box'
import theme, { colors } from './theme'
import { LauncherWindow } from './components/launcher'
import SystemStatus from './components/SystemStatus'
import AppMark from './components/brand/AppMark'
import appConfig from '@app-config'

export default function App() {
  const [view, setView] = useState('launcher')

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {view === 'launcher' ? (
        <Box sx={{ position: 'relative', height: '100vh' }}>
          <LauncherWindow />
          <IconButton
            aria-label={`${appConfig.name} — open system status`}
            onClick={() => setView('status')}
            size="small"
            sx={{
              position: 'absolute',
              top: 12,
              right: 12,
              zIndex: 3,
              p: 0.5,
              borderRadius: 2,
              opacity: 0.92,
              transition: 'opacity 160ms ease, background-color 160ms ease, transform 160ms ease',
              '&:hover': {
                opacity: 1,
                bgcolor: colors.hover,
                transform: 'scale(1.04)',
              },
            }}
          >
            <AppMark size={32} />
          </IconButton>
        </Box>
      ) : (
        <SystemStatus onBack={() => setView('launcher')} />
      )}
    </ThemeProvider>
  )
}
