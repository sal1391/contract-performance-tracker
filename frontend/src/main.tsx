import React from 'react'
import ReactDOM from 'react-dom/client'
import { Auth0Provider } from '@auth0/auth0-react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CssBaseline, ThemeProvider } from '@mui/material'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { theme } from './theme'

const queryClient = new QueryClient()

const domain = import.meta.env.VITE_AUTH0_DOMAIN as string | undefined
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID as string | undefined
const audience = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined

// Wrap in Auth0 only when configured; otherwise run open (dev backend uses its dev user).
function Providers({ children }: { children: React.ReactNode }) {
  const inner = (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>{children}</BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
  if (!domain || !clientId) return inner
  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{ redirect_uri: window.location.origin, audience }}
    >
      {inner}
    </Auth0Provider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Providers>
      <App />
    </Providers>
  </React.StrictMode>,
)
