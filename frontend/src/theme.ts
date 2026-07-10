import { alpha, createTheme } from '@mui/material/styles'

const ink = '#12303a'
const teal = '#0b4f5c'
const deepTeal = '#083944'
const brass = '#b57a45'
const mist = '#edf4f5'

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: teal,
      dark: deepTeal,
      light: '#dbecef',
      contrastText: '#ffffff',
    },
    secondary: {
      main: brass,
      dark: '#8a5a2e',
      light: '#efe1d2',
    },
    error: {
      main: '#c55f43',
    },
    success: {
      main: '#2d7b5a',
    },
    warning: {
      main: '#c38a2b',
    },
    background: {
      default: mist,
      paper: '#ffffff',
    },
    text: {
      primary: ink,
      secondary: '#5a7078',
    },
    divider: alpha(teal, 0.12),
  },
  shape: {
    borderRadius: 18,
  },
  typography: {
    fontFamily: ['"Segoe UI"', 'Aptos', '"Helvetica Neue"', 'Arial', 'sans-serif'].join(','),
    h4: {
      fontSize: '2.2rem',
      fontWeight: 700,
      letterSpacing: '-0.03em',
    },
    h5: {
      fontSize: '1.9rem',
      fontWeight: 700,
      letterSpacing: '-0.03em',
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
    },
    overline: {
      fontSize: '0.72rem',
      fontWeight: 700,
      letterSpacing: '0.12em',
      textTransform: 'uppercase',
    },
    button: {
      fontWeight: 700,
      textTransform: 'none',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          minHeight: '100vh',
          background:
            'radial-gradient(circle at top left, rgba(11,79,92,0.08), transparent 32%), linear-gradient(180deg, #edf4f5 0%, #f7fbfb 42%, #edf2f2 100%)',
        },
        '#root': {
          minHeight: '100vh',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: `1px solid ${alpha(teal, 0.08)}`,
          boxShadow: '0 18px 44px rgba(8, 38, 46, 0.08)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          paddingInline: 16,
        },
        contained: {
          boxShadow: '0 10px 24px rgba(11, 79, 92, 0.18)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontWeight: 700,
        },
      },
    },
  },
})
