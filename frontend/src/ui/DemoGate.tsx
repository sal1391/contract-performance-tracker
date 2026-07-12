import { useState, type FormEvent } from 'react'
import { Alert, Box, Button, Stack, Typography } from '@mui/material'

// Demo-mode-only access gate (Start button, no email). Entirely separate from Auth0 — see
// App.tsx, which only renders this when VITE_DEMO_MODE is set, before the Auth0 branch is
// reached at all.
const GATE_KEY = 'demo_gate_passed'

const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined
const API_BASE = (import.meta.env.VITE_API_BASE as string) || '/api'

declare global {
  interface Window {
    __demoGateTurnstileToken?: string
    onDemoGateTurnstile?: (token: string) => void
  }
}

if (TURNSTILE_SITE_KEY && typeof window !== 'undefined') {
  window.onDemoGateTurnstile = (token: string) => {
    window.__demoGateTurnstileToken = token
  }
}

export function demoGatePassed(): boolean {
  return localStorage.getItem(GATE_KEY) === '1'
}

export default function DemoGate({ onPass }: { onPass: () => void }) {
  const [website, setWebsite] = useState('') // honeypot — real visitors never touch this
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/demo/gate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          website,
          turnstile_token: window.__demoGateTurnstileToken || '',
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data.ok) {
        throw new Error(data.detail || 'Could not verify — please try again.')
      }
      localStorage.setItem(GATE_KEY, '1')
      onPass()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not verify — please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', px: 2 }}>
      {TURNSTILE_SITE_KEY && (
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer />
      )}
      <Box
        component="form"
        onSubmit={handleSubmit}
        sx={{
          width: 'min(100%, 460px)',
          p: 4,
          borderRadius: 6,
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        <Stack spacing={2}>
          <Typography variant="overline" color="secondary.main">
            Fuel contract tracker — demo
          </Typography>
          <Typography variant="h4">See the live demo</Typography>
          <Typography color="text.secondary">
            Start this read-only demo workspace. No account or password needed.
          </Typography>

          {/* Honeypot: off-screen for real users; bots that fill every field trip it. */}
          <input
            type="text"
            name="website"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            tabIndex={-1}
            autoComplete="off"
            aria-hidden="true"
            style={{ position: 'absolute', left: -9999 }}
          />

          {TURNSTILE_SITE_KEY && (
            <div
              className="cf-turnstile"
              data-sitekey={TURNSTILE_SITE_KEY}
              data-callback="onDemoGateTurnstile"
            />
          )}

          {error && <Alert severity="error">{error}</Alert>}

          <Button type="submit" variant="contained" disabled={submitting}>
            {submitting ? 'Starting…' : 'Start'}
          </Button>

          <Typography variant="caption" color="text.secondary">
            We record your IP address to prevent abuse — no marketing, no tracking.{' '}
            <a href="/privacy">See our Privacy Notice</a>.
          </Typography>
        </Stack>
      </Box>
    </Box>
  )
}
