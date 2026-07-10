import { useAuth0 } from '@auth0/auth0-react'
import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded'
import EditNoteRoundedIcon from '@mui/icons-material/EditNoteRounded'
import GroupsRoundedIcon from '@mui/icons-material/GroupsRounded'
import HubRoundedIcon from '@mui/icons-material/HubRounded'
import ManageAccountsRoundedIcon from '@mui/icons-material/ManageAccountsRounded'
import { useQuery } from '@tanstack/react-query'
import { Box, Button, Chip, MenuItem, Select, Stack, Typography } from '@mui/material'
import { Navigate, Route, Routes } from 'react-router-dom'
import Accounts from './pages/Accounts'
import AccountDetail from './pages/AccountDetail'
import Admin from './pages/Admin'
import Dashboard from './pages/Dashboard'
import Mapping from './pages/Mapping'
import RiskLines from './pages/RiskLines'
import Workbench from './pages/Workbench'
import { getActAs, setActAs, useApi } from './api'
import { AppShell } from './ui/layout'

type DevUser = { id: string; email: string; display_name: string | null; role_level: string }

const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Admin',
  IC: 'Individual contributor',
  OFFICE_MANAGER: 'Office manager',
  REGIONAL_DIRECTOR: 'Regional director',
  SEGMENT_LEAD: 'Segment lead',
  LEADERSHIP: 'Leadership',
}

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: <DashboardRoundedIcon fontSize="small" /> },
  { to: '/accounts', label: 'Accounts', icon: <GroupsRoundedIcon fontSize="small" /> },
  { to: '/workbench', label: 'Workbench', icon: <EditNoteRoundedIcon fontSize="small" /> },
  { to: '/mapping', label: 'Mapping', icon: <HubRoundedIcon fontSize="small" /> },
  { to: '/admin', label: 'Admin', icon: <ManageAccountsRoundedIcon fontSize="small" /> },
]

function roleLabel(roleLevel: string | null | undefined) {
  if (!roleLevel) return 'Unknown role'
  return ROLE_LABELS[roleLevel] ?? roleLevel.replaceAll('_', ' ').toLowerCase()
}

function userLabel(user: DevUser | null | undefined) {
  if (!user) return 'ADMIN - dev (see all)'
  return `${user.display_name ?? user.email} (${roleLabel(user.role_level)})`
}

function ActAsSwitcher() {
  const api = useApi()
  const users = useQuery<DevUser[]>({
    queryKey: ['dev-users'],
    queryFn: async () => (await api.get('/dev/users')).data,
  })
  const current = getActAs()
  const currentUser = (users.data ?? []).find((u) => u.id === current)
  const currentRole = current ? roleLabel(currentUser?.role_level) : 'Admin'

  return (
    <Stack
      direction={{ xs: 'column', md: 'row' }}
      spacing={1}
      sx={{ alignItems: { xs: 'stretch', md: 'center' } }}
    >
      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
        <Chip size="small" label="Act as" variant="outlined" />
        <Chip size="small" label={`Role: ${currentRole}`} variant="outlined" />
      </Stack>
      <Select
        size="small"
        variant="outlined"
        value={current}
        displayEmpty
        onChange={(e) => setActAs(e.target.value as string)}
        renderValue={(value) => {
          const selectedUser = (users.data ?? []).find((u) => u.id === value)
          return (
            <Box
              component="span"
              sx={{
                display: 'block',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {userLabel(selectedUser)}
            </Box>
          )
        }}
        sx={{
          minWidth: { xs: '100%', sm: 320, md: 380 },
          maxWidth: 460,
          '& .MuiSelect-select': {
            py: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          },
        }}
      >
        <MenuItem value="">ADMIN - dev (see all)</MenuItem>
        {(users.data ?? []).map((u) => (
          <MenuItem key={u.id} value={u.id}>
            <Stack spacing={0.15} sx={{ minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {u.display_name ?? u.email}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {roleLabel(u.role_level)}
              </Typography>
            </Stack>
          </MenuItem>
        ))}
      </Select>
    </Stack>
  )
}

export default function App() {
  const { isAuthenticated, isLoading, loginWithRedirect, logout, user } = useAuth0()
  const authConfigured = Boolean(import.meta.env.VITE_AUTH0_DOMAIN)

  if (authConfigured && isLoading) return <Box sx={{ p: 4 }}>Loading...</Box>
  if (authConfigured && !isAuthenticated) {
    return (
      <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', px: 2 }}>
        <Box
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
              Fuel contract tracker
            </Typography>
            <Typography variant="h4">Sign in to the workspace</Typography>
            <Typography color="text.secondary">
              Review contract performance, work bid lines, and manage mapping without leaving the
              operating surface.
            </Typography>
            <Button variant="contained" onClick={() => loginWithRedirect()}>
              Sign in
            </Button>
          </Stack>
        </Box>
      </Box>
    )
  }

  const utility = authConfigured ? (
    <Button color="inherit" onClick={() => logout()}>
      {user?.email ?? 'Sign out'}
    </Button>
  ) : (
    <ActAsSwitcher />
  )

  return (
    <AppShell brand="Contract tracking" navItems={NAV_ITEMS} utility={utility}>
      <Box sx={{ minWidth: 0 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/risk/:status" element={<RiskLines />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/accounts/:customerGroupNumber" element={<AccountDetail />} />
          <Route path="/workbench" element={<Workbench />} />
          <Route path="/mapping" element={<Mapping />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Box>
    </AppShell>
  )
}
