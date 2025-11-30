import { createTheme } from '@mui/material/styles'

const baseOptions = {
  palette: {
    primary: {
      main: '#7c3aed',
    },
    secondary: {
      main: '#06b6d4',
    },
    success: {
      main: '#22c55e',
    },
    error: {
      main: '#ef4444',
    },
  },
  typography: {
    fontFamily: 'Roboto, Inter, system-ui, -apple-system, sans-serif',
    h1: {
      fontWeight: 800,
      letterSpacing: '-0.02em',
    },
    h4: {
      fontWeight: 700,
      letterSpacing: '-0.01em',
    },
    body1: {
      lineHeight: 1.7,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 18,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
}

export const getTheme = (mode = 'dark') =>
  createTheme({
    ...baseOptions,
    palette: {
      ...baseOptions.palette,
      mode,
      background:
        mode === 'dark'
          ? { default: '#0b1021', paper: '#111827' }
          : { default: '#f9fafb', paper: '#ffffff' },
    },
  })

export default getTheme
