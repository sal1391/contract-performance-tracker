import { useMemo, useState } from 'react'
import { Box, Button, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { DataGrid, type GridColDef } from '@mui/x-data-grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApi } from '../api'

const STATUS_LABEL: Record<string, string> = {
  AUTO_SUGGESTED: 'Auto', CONFIRMED: 'Confirmed', USER_ADDED: 'Manual', EXCLUDED: 'Excluded',
}

export default function Mapping() {
  const api = useApi()
  const qc = useQueryClient()
  const [lineId, setLineId] = useState('')

  const get = (url: string) => async () => (await api.get(url)).data
  const lines = useQuery<any[]>({ queryKey: ['bid-lines', 'all'], queryFn: get('/bid-lines') })
  const lifts = useQuery<any[]>({ queryKey: ['lifts'], queryFn: get('/lifts') })
  const mappings = useQuery<any[]>({
    queryKey: ['mappings', lineId],
    queryFn: get(`/mappings/by-line/${lineId}`),
    enabled: Boolean(lineId),
  })

  const refresh = () => qc.invalidateQueries({ queryKey: ['mappings', lineId] })
  const autoMatch = useMutation({ mutationFn: async () => (await api.post(`/bid-lines/${lineId}/auto-match`)).data, onSuccess: refresh })
  const confirm = useMutation({ mutationFn: async (id: string) => (await api.post(`/mappings/${id}/confirm`)).data, onSuccess: refresh })
  const unmap = useMutation({ mutationFn: async (id: string) => (await api.post(`/mappings/${id}/exclude`)).data, onSuccess: refresh })
  const addManual = useMutation({
    mutationFn: async (liftId: string) => (await api.post('/mappings', { bid_line_id: lineId, lift_id: liftId })).data,
    onSuccess: refresh,
  })

  const mappedIds = useMemo(() => new Set((mappings.data ?? []).map((m) => m.lift_id)), [mappings.data])
  const available = useMemo(() => (lifts.data ?? []).filter((p) => !mappedIds.has(p.lift_id)), [lifts.data, mappedIds])

  const mappedCols: GridColDef[] = [
    { field: 'lift_id', headerName: 'LIFT', width: 120 },
    { field: 'status', headerName: 'Status', width: 110, renderCell: (p) => STATUS_LABEL[p.value] ?? p.value },
    { field: 'match_score', headerName: 'Score', width: 80, type: 'number' },
    { field: 'override_reason', headerName: 'Reason', width: 200 },
    {
      field: 'actions', headerName: 'Actions', width: 200, sortable: false,
      renderCell: (p) => (
        <Stack direction="row" spacing={1}>
          <Button size="small" onClick={() => confirm.mutate(p.row.id)}>Confirm</Button>
          <Button size="small" color="error" onClick={() => unmap.mutate(p.row.id)}>Unmap</Button>
        </Stack>
      ),
    },
  ]
  const liftCols: GridColDef[] = [
    { field: 'lift_id', headerName: 'LIFT', width: 110 },
    { field: 'customer_group_number', headerName: 'Customer', width: 110 },
    { field: 'port', headerName: 'Port', width: 100 },
    { field: 'grade', headerName: 'Grade', width: 90 },
    { field: 'supplier_number', headerName: 'Supplier', width: 100 },
    { field: 'volume_tons', headerName: 'Tons', width: 90, type: 'number' },
    { field: 'gp', headerName: 'GP', width: 100, type: 'number' },
    {
      field: 'actions', headerName: '', width: 90, sortable: false,
      renderCell: (p) => <Button size="small" onClick={() => addManual.mutate(p.row.lift_id)}>Map</Button>,
    },
  ]

  return (
    <Box>
      <Typography variant="h5" gutterBottom>LIFT → Contract mapping</Typography>
      <Stack direction="row" spacing={2} sx={{ mb: 2, alignItems: 'center' }}>
        <TextField select label="Bid line" value={lineId} onChange={(e) => setLineId(e.target.value)} sx={{ minWidth: 420 }}>
          {(lines.data ?? []).map((l) => (
            <MenuItem key={l.id} value={l.id}>
              QB {l.contract_source_id} · {l.port} {l.grade} · {l.supplier_name}
            </MenuItem>
          ))}
        </TextField>
        <Button variant="contained" disabled={!lineId || autoMatch.isPending} onClick={() => autoMatch.mutate()}>
          Run auto-match
        </Button>
      </Stack>

      {lineId && (
        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" gutterBottom>Mapped Lifts</Typography>
            <div style={{ height: 420, width: '100%' }}>
              <DataGrid rows={mappings.data ?? []} columns={mappedCols} getRowId={(r) => r.id} loading={mappings.isLoading} />
            </div>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" gutterBottom>Available Lifts</Typography>
            <div style={{ height: 420, width: '100%' }}>
              <DataGrid rows={available} columns={liftCols} getRowId={(r) => r.lift_id} loading={lifts.isLoading} />
            </div>
          </Box>
        </Stack>
      )}
    </Box>
  )
}
