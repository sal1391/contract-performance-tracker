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
            This site hosts a set of product demos. To limit abuse, each demo asks for your email
            address before you can start. This page explains what we do with it.
          </Typography>

          <Stack spacing={1}>
            <Typography variant="h6">What we collect</Typography>
            <List sx={{ listStyleType: 'disc', pl: 3, py: 0 }}>
              <ListItem sx={{ display: 'list-item', px: 0, py: 0.5 }}>
                The email address you enter to start a demo.
              </ListItem>
              <ListItem sx={{ display: 'list-item', px: 0, py: 0.5 }}>
                Standard hosting/request logs generated automatically by our hosting provider
                (Railway), such as IP address and request timestamps.
              </ListItem>
            </List>
            <Typography>
              We do not use cookies, analytics, or third-party tracking scripts on these demo
              pages.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Why we collect it</Typography>
            <Typography>
              Solely to prevent abuse and misuse of the demos (e.g. rate-limiting, blocking bad
              actors). We do not use your email for marketing, and we do not send you any emails.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Sharing</Typography>
            <Typography>
              We do not sell or share your email address with third parties. It is stored only
              for the purpose described above.
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="h6">Retention</Typography>
            <Typography>
              Email addresses collected here are kept for 30 days, after which they are deleted.
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
              You can ask us to delete your email address at any time by contacting{' '}
              <Link href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</Link>. We will remove it
              within a reasonable time.
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
