import { useMemo, useState } from 'react'
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem,
  Stack, TextField, Typography,
} from '@mui/material'
import { DataGrid, type GridColDef } from '@mui/x-data-grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApi } from '../api'

const UNIT_TYPES = ['COMPANY', 'SEGMENT', 'REGION', 'OFFICE']
const ROLES = ['IC', 'OFFICE_MANAGER', 'REGIONAL_DIRECTOR', 'SEGMENT_LEAD', 'LEADERSHIP', 'ADMIN']
const s = (v: any) => (v == null ? '' : String(v))

type Unit = { id: string; name: string; unit_type: string; parent_id: string | null; is_active: boolean; is_verified: boolean }
type User = {
  id: string; email: string; display_name: string | null; role_level: string
  home_office_id: string | null; scope_unit_id: string | null; is_active: boolean
  source: string | null; role_locked: boolean
}

export default function Admin() {
  const api = useApi()
  const qc = useQueryClient()
  const get = (url: string) => async () => (await api.get(url)).data
  const units = useQuery<Unit[]>({ queryKey: ['org-units'], queryFn: get('/org/units'), retry: false })
  const users = useQuery<User[]>({ queryKey: ['org-users'], queryFn: get('/org/users'), retry: false })

  const unitName = useMemo(() => {
    const m = new Map<string, string>()
    ;(units.data ?? []).forEach((u) => m.set(u.id, u.name))
    return (id: string | null) => (id ? m.get(id) ?? id : '—')
  }, [units.data])
  const offices = (units.data ?? []).filter((u) => u.unit_type === 'OFFICE')

  const forbidden = (units.error as any)?.response?.status === 403

  // ---------- org unit dialog ----------
  const emptyUnit = { name: '', unit_type: 'OFFICE', parent_id: '' }
  const [unitOpen, setUnitOpen] = useState(false)
  const [unit, setUnit] = useState<any>(emptyUnit)
  const [editUnitId, setEditUnitId] = useState<string | null>(null)
  const openNewUnit = () => { setUnit(emptyUnit); setEditUnitId(null); setUnitOpen(true) }
  const openEditUnit = (r: Unit) => {
    setUnit({ name: r.name, unit_type: r.unit_type, parent_id: s(r.parent_id) })
    setEditUnitId(r.id); setUnitOpen(true)
  }
  const saveUnit = useMutation({
    mutationFn: async () => {
      const body = { name: unit.name, unit_type: unit.unit_type, parent_id: unit.parent_id || null }
      return editUnitId
        ? (await api.patch(`/org/units/${editUnitId}`, body)).data
        : (await api.post('/org/units', body)).data
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['org-units'] }); setUnitOpen(false) },
  })
  const deleteUnit = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/org/units/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['org-units'] }),
  })
  const verifyUnit = useMutation({
    mutationFn: async (id: string) => (await api.post(`/org/units/${id}/verify`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['org-units'] }),
  })
  const mergeUnit = useMutation({
    mutationFn: async ({ id, into }: { id: string; into: string }) =>
      (await api.post(`/org/units/${id}/merge`, { into_id: into })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['org-units'] }); qc.invalidateQueries({ queryKey: ['org-users'] }) },
  })
  const runSync = useMutation({
    mutationFn: async () => (await api.post('/org/sync')).data,
    onSuccess: (r: any) => { qc.invalidateQueries({ queryKey: ['org-units'] }); qc.invalidateQueries({ queryKey: ['org-users'] });
      window.alert(r.status === 'ok' ? `Synced: ${JSON.stringify(r)}` : `Sync skipped: ${r.reason}`) },
  })

  // ---------- user dialog ----------
  const emptyUser = { email: '', display_name: '', role_level: 'IC', home_office_id: '', scope_unit_id: '', role_locked: false }
  const [userOpen, setUserOpen] = useState(false)
  const [u, setU] = useState<any>(emptyUser)
  const [editUserId, setEditUserId] = useState<string | null>(null)
  const openNewUser = () => { setU(emptyUser); setEditUserId(null); setUserOpen(true) }
  const openEditUser = (r: User) => {
    setU({ email: r.email, display_name: s(r.display_name), role_level: r.role_level,
      home_office_id: s(r.home_office_id), scope_unit_id: s(r.scope_unit_id), role_locked: r.role_locked })
    setEditUserId(r.id); setUserOpen(true)
  }
  const saveUser = useMutation({
    mutationFn: async () => {
      const body: any = {
        display_name: u.display_name || null, role_level: u.role_level,
        home_office_id: u.home_office_id || null, scope_unit_id: u.scope_unit_id || null,
        role_locked: u.role_level !== 'IC' ? true : Boolean(u.role_locked),
      }
      if (!editUserId) body.email = u.email
      return editUserId
        ? (await api.patch(`/org/users/${editUserId}`, body)).data
        : (await api.post('/org/users', body)).data
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['org-users'] }); setUserOpen(false) },
  })

  const editBtn = (handler: (r: any) => void): GridColDef => ({
    field: 'edit', headerName: '', width: 64, sortable: false,
    renderCell: (p) => <Button size="small" onClick={() => handler(p.row)}>Edit</Button>,
  })
  const unitCols: GridColDef[] = [
    editBtn(openEditUnit),
    { field: 'name', headerName: 'Name', width: 170 },
    { field: 'unit_type', headerName: 'Type', width: 120 },
    { field: 'parent_id', headerName: 'Parent', width: 170, valueGetter: (v) => unitName(v as string | null) },
    { field: 'is_verified', headerName: 'Verified', width: 110,
      renderCell: (p) => p.row.is_verified
        ? <span>Yes</span>
        : <Button size="small" onClick={() => verifyUnit.mutate(p.row.id)}>Verify</Button> },
    { field: 'merge', headerName: '', width: 80, sortable: false,
      renderCell: (p) => <Button size="small" onClick={() => {
        const into = window.prompt('Merge into which unit id? (copy an id from this table)')
        if (into) mergeUnit.mutate({ id: p.row.id, into })
      }}>Merge</Button> },
    {
      field: 'del', headerName: '', width: 80, sortable: false,
      renderCell: (p) => (
        <Button size="small" color="error"
          onClick={() => { if (confirm(`Delete org unit "${p.row.name}"?`)) deleteUnit.mutate(p.row.id) }}>
          Delete
        </Button>
      ),
    },
  ]
  const userCols: GridColDef[] = [
    editBtn(openEditUser),
    { field: 'display_name', headerName: 'Name', width: 200, valueGetter: (v, r) => v ?? r.email },
    { field: 'email', headerName: 'Email', width: 200 },
    { field: 'role_level', headerName: 'Role', width: 160 },
    { field: 'scope_unit_id', headerName: 'Sees (scope)', width: 160, valueGetter: (v) => unitName(v as string | null) },
    { field: 'home_office_id', headerName: 'Home office', width: 160, valueGetter: (v) => unitName(v as string | null) },
    { field: 'source', headerName: 'Source', width: 100 },
    { field: 'role_locked', headerName: 'Locked', width: 90, valueGetter: (v) => (v ? 'yes' : '') },
  ]

  // org-unit option list, excluding a given id (so a unit can't be made its own parent)
  const unitOptions = (list: Unit[], excludeId?: string | null) => (
    [<MenuItem key="" value="">—</MenuItem>,
      ...list.filter((o) => o.id !== excludeId)
        .map((o) => <MenuItem key={o.id} value={o.id}>{o.name} · {o.unit_type}</MenuItem>)]
  )
  const userUnitSelect = (label: string, field: 'home_office_id' | 'scope_unit_id', list: Unit[]) => (
    <TextField select fullWidth size="small" label={label} value={u[field]}
      onChange={(e) => setU({ ...u, [field]: e.target.value })}>
      {unitOptions(list)}
    </TextField>
  )

  if (forbidden) {
    return (
      <Alert severity="info">
        Org administration is ADMIN-only. You are currently acting as a non-admin user — switch
        “Act as” back to <b>ADMIN — dev (see all)</b> (top-right) to manage the org tree and users.
      </Alert>
    )
  }

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5">Org units</Typography>
        <Stack direction="row">
          <Button variant="outlined" sx={{ mr: 1 }} onClick={() => runSync.mutate()}>Run sales-planning sync</Button>
          <Button variant="contained" onClick={openNewUnit}>+ New unit</Button>
        </Stack>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        Company → Segment → Region → Office. Editing the tree rebuilds the closure that drives row-level visibility.
      </Typography>
      <div style={{ height: 320, width: '100%', marginTop: 12 }}>
        <DataGrid rows={units.data ?? []} columns={unitCols} getRowId={(r) => r.id} loading={units.isLoading} />
      </div>

      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mt: 4 }}>
        <Typography variant="h5">Users</Typography>
        <Button variant="contained" onClick={openNewUser}>+ New user</Button>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        “Sees (scope)” sets each user's visible subtree; “Home office” is where their new bids land.
      </Typography>
      <div style={{ height: 360, width: '100%', marginTop: 12 }}>
        <DataGrid rows={users.data ?? []} columns={userCols} getRowId={(r) => r.id} loading={users.isLoading} />
      </div>

      {/* org unit dialog */}
      <Dialog open={unitOpen} onClose={() => setUnitOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editUnitId ? 'Edit org unit' : 'New org unit'}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Name" size="small" value={unit.name}
              onChange={(e) => setUnit({ ...unit, name: e.target.value })} />
            <TextField select label="Type" size="small" value={unit.unit_type}
              onChange={(e) => setUnit({ ...unit, unit_type: e.target.value })}>
              {UNIT_TYPES.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
            </TextField>
            <TextField select fullWidth size="small" label="Parent" value={unit.parent_id}
              onChange={(e) => setUnit({ ...unit, parent_id: e.target.value })}>
              {unitOptions(units.data ?? [], editUnitId)}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUnitOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={!unit.name || saveUnit.isPending} onClick={() => saveUnit.mutate()}>
            {editUnitId ? 'Save' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* user dialog */}
      <Dialog open={userOpen} onClose={() => setUserOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editUserId ? 'Edit user' : 'New user'}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Email" size="small" value={u.email} disabled={Boolean(editUserId)}
              onChange={(e) => setU({ ...u, email: e.target.value })} />
            <TextField label="Display name" size="small" value={u.display_name}
              onChange={(e) => setU({ ...u, display_name: e.target.value })} />
            <TextField select label="Role" size="small" value={u.role_level}
              onChange={(e) => setU({ ...u, role_level: e.target.value })}>
              {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
            </TextField>
            {userUnitSelect('Sees (scope unit)', 'scope_unit_id', units.data ?? [])}
            {userUnitSelect('Home office', 'home_office_id', offices)}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUserOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={!u.email || saveUser.isPending} onClick={() => saveUser.mutate()}>
            {editUserId ? 'Save' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
