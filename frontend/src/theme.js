import { createTheme } from '@mui/material/styles'

/**
 * MosAIq brand palette (from identity guide).
 * Single source of truth — do not scatter hex values in components.
 */
export const colors = {
  // Brand accents
  accentTeal: '#00E5A8',
  accentGreen: '#22C55E',
  cyan: '#06B6D4',
  blue: '#2563EB',

  // Surfaces
  background: '#0D1117',
  surface: '#151B24',
  border: '#243040',
  hover: '#1A2433',

  // Text
  textPrimary: '#E8EEF2',
  textSecondary: '#8CA3A0',

  // Primary interactive accent (wordmark "AI", focus rings, search glyph)
  accent: '#00E5A8',

  // Mosaic idle grid
  mosaicDim: 'rgba(0, 229, 168, 0.045)',
  mosaicGlowTeal: 'rgba(0, 229, 168, 0.22)',
  mosaicGlowCyan: 'rgba(6, 182, 212, 0.18)',
  mosaicGlowBlue: 'rgba(37, 99, 235, 0.16)',
}

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: colors.accentTeal,
      light: '#5FF0C8',
      dark: '#00B884',
    },
    secondary: {
      main: colors.cyan,
      light: '#67E8F9',
      dark: colors.blue,
    },
    background: {
      default: colors.background,
      paper: colors.surface,
    },
    divider: colors.border,
    text: {
      primary: colors.textPrimary,
      secondary: colors.textSecondary,
    },
    success: {
      main: colors.accentGreen,
    },
    info: {
      main: colors.cyan,
    },
    error: {
      main: '#EF5350',
    },
    action: {
      hover: colors.hover,
    },
  },
  typography: {
    fontFamily: '"Segoe UI", "SF Pro Text", system-ui, sans-serif',
    h4: {
      fontWeight: 600,
      letterSpacing: '-0.02em',
    },
    body1: {
      letterSpacing: '0.01em',
    },
    body2: {
      fontSize: '0.8125rem',
      letterSpacing: '0.01em',
    },
    caption: {
      fontSize: '0.75rem',
      letterSpacing: '0.02em',
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: colors.background,
          color: colors.textPrimary,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
})

export default theme
