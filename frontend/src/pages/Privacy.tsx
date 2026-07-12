import { Box, Link, List, ListItem, Stack, Typography } from '@mui/material'

// Rendered outside the demo gate and Auth0 flows — see App.tsx, which checks
// window.location.pathname before either gate so /privacy is always reachable.
const LAST_UPDATED = 'July 11, 2026'
const CONTACT_EMAIL = 'carlos.salgado30@yahoo.com'

export default function Privacy() {
  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', px: 2, py: 6 }}>
      <Box sx={{ width: 'min(100%, 720px)' }}>
        <Stack spacing={3}>
          <Stack spacing={0.5}>
            <Typography variant="h4">Privacy Notice</Typography>
            <Typography color="text.secondary">Last updated: {LAST_UPDATED}</Typography>
          </Stack>

          <Typography>
            This site hosts a set of product demos. To limit abuse, we record basic technical
            information when you use a demo. This page explains what.
          </Typography>

          <Stack spacing={1}>
            <Typography variant="h6">What we collect</Typography>
            <List sx={{ listStyleType: 'disc', pl: 3, py: 0 }}>
              <ListItem sx={{ display: 'list-item', px: 0, py: 0.5 }}>
                Your IP address and request timestamps, recorded when you start a demo, used to
                prevent abuse (e.g. rate-limiting, blocking bad actors).
              </ListItem>
              <ListItem sx={{ display: 'list-item', px: 0, py: 0.5 }}>
                Standard hosting/request logs generated automatically by our hosting provider
                (Railway).
              </ListItem>
            </List>
            <Typography>
              We do not ask for your email or any account details, and we do not use cookies,
              analytics, or third-party tracking scripts on these demo pages.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Why we collect it</Typography>
            <Typography>
              Solely to prevent abuse and misuse of the demos. We do not use this information for
              marketing.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Sharing</Typography>
            <Typography>
              We do not sell or share this information with third parties. It is used only for
              the purpose described above.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Retention</Typography>
            <Typography>
              Abuse-prevention records (IP address and timestamps) are kept for 30 days, after
              which they are deleted.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">These demos</Typography>
            <Typography>
              These are demo/test environments, not production services. Please don&apos;t enter
              real, sensitive, or production data into any of them.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Your choices</Typography>
            <Typography>
              You can ask us about or request deletion of the technical records tied to your IP
              address at any time by contacting{' '}
              <Link href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</Link>.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Contact</Typography>
            <Typography>
              Questions about this notice: <Link href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</Link>
            </Typography>
          </Stack>
        </Stack>
      </Box>
    </Box>
  )
}
