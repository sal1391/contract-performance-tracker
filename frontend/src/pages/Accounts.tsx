import { useState } from 'react'
import { Box, TextField } from '@mui/material'
import { DataGrid, type GridColDef } from '@mui/x-data-grid'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../api'
import { PageHeader, WorkspacePanel } from '../ui/layout'

const money = (v: any) => (v == null || v === '' ? '' : `$${Math.round(Number(v)).toLocaleString()}`)
const tons = (v: any) => (v == null || v === '' ? '' : Math.round(Number(v)).toLocaleString())
const winPct = (v: any) => (v == null ? '-' : `${Math.round(Number(v) * 100)}%`)

export default function Accounts() {
  const api = useApi()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const get = (url: string, params?: any) => async () => (await api.get(url, { params })).data
  const accounts = useQuery<any[]>({
    queryKey: ['accounts', search],
    queryFn: get('/accounts', { q: search || undefined }),
  })

  const cols: GridColDef[] = [
    {
      field: 'customer_group_name',
      headerName: 'Customer',
      width: 200,
      valueGetter: (_v, row) => row.customer_group_name ?? row.customer_group_number,
    },
    { field: 'contract_count', headerName: 'Contracts', width: 100, type: 'number' },
    { field: 'line_count', headerName: 'Lines', width: 90, type: 'number' },
    { field: 'gp_won', headerName: 'GP Won', width: 110, type: 'number', valueFormatter: money },
    { field: 'gp_pending', headerName: 'GP Pending', width: 120, type: 'number', valueFormatter: money },
    { field: 'gp_lost', headerName: 'GP Lost', width: 110, type: 'number', valueFormatter: money },
    { field: 'win_rate', headerName: 'Win %', width: 90, type: 'number', valueFormatter: winPct },
    { field: 'volume_won', headerName: 'Vol Won', width: 110, type: 'number', valueFormatter: tons },
    {
      field: 'volume_pending',
      headerName: 'Vol Pending',
      width: 120,
      type: 'number',
      valueFormatter: tons,
    },
  ]

  return (
    <Box>
      <PageHeader
        eyebrow="Accounts"
        title="Customer accounts"
        subtitle="Roll up contract performance by customer, then drill into the exact contracts and bid lines behind the commercial picture."
      />
      <WorkspacePanel
        title="Account list"
        subtitle="Click any customer row to open its contract stack and bid-line detail."
      >
        <TextField
          size="small"
          label="Search customer"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ mb: 1.5, width: { xs: '100%', md: 360 } }}
        />
        <div style={{ height: 540, width: '100%' }}>
          <DataGrid
            rows={accounts.data ?? []}
            columns={cols}
            getRowId={(r) => r.customer_group_number}
            loading={accounts.isLoading}
            onRowClick={(p) => navigate(`/accounts/${encodeURIComponent(String(p.id))}`)}
          />
        </div>
      </WorkspacePanel>
    </Box>
  )
}
