import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#4caf50',
      light: '#81c784',
      dark: '#388e3c',
    },
    secondary: {
      main: '#a5d6a7',
    },
    background: {
      default: '#0f1410',
      paper: '#1a211c',
    },
    text: {
      primary: '#e8f5e9',
      secondary: '#a5b5a8',
    },
    success: {
      main: '#66bb6a',
    },
    error: {
      main: '#ef5350',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Segoe UI", system-ui, sans-serif',
  },
  shape: {
    borderRadius: 8,
  },
})

export default theme
