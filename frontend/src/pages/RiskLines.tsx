import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import { Box, Button, Chip, Stack } from '@mui/material'
import { DataGrid, type GridColDef } from '@mui/x-data-grid'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom'
import { useApi } from '../api'
import { RISK_LABELS, riskChipColor, riskLabel } from '../risk'
import { PageHeader, WorkspacePanel } from '../ui/layout'

type RiskLine = {
  bid_line_id: string
  contract_id: string
  contract_source_id: string | null
  customer_group_number: string | null
  customer_group_name: string | null
  port: string | null
  grade: string | null
  supplier_name: string | null
  risk_status: string
  contracted_volume: number | null
  actual_volume: number | null
  contracted_gp: number | null
  actual_gp: number | null
  elapsed_pct: number | null
  contract_end: string | null
}

const money = (v: any) => (v == null || v === '' ? '' : `$${Math.round(Number(v)).toLocaleString()}`)
const tons = (v: any) => (v == null || v === '' ? '' : Math.round(Number(v)).toLocaleString())
const pctFmt = (v: any) => (v == null || v === '' ? '' : `${Math.round(Number(v) * 100)}%`)

export default function RiskLines() {
  const api = useApi()
  const navigate = useNavigate()
  const { status = '' } = useParams()
  const statuses = status.split(',').filter(Boolean)
  const known = statuses.length > 0 && statuses.every((s) => s in RISK_LABELS)

  const lines = useQuery<RiskLine[]>({
    queryKey: ['risk-lines', status],
    enabled: known,
    queryFn: async () => {
      const qs = statuses.map((s) => `status=${encodeURIComponent(s)}`).join('&')
      return (await api.get(`/dashboard/risk-lines?${qs}`)).data
    },
  })

  const cols: GridColDef[] = [
    {
      field: 'customer_group_name',
      headerName: 'Customer',
      width: 190,
      valueGetter: (_v, row) => row.customer_group_name ?? row.customer_group_number ?? '-',
    },
    { field: 'contract_source_id', headerName: 'QB ID', width: 100 },
    { field: 'port', headerName: 'Port', width: 110 },
    { field: 'grade', headerName: 'Grade', width: 90 },
    { field: 'supplier_name', headerName: 'Supplier', width: 130 },
    {
      field: 'contracted_volume',
      headerName: 'Contracted',
      width: 110,
      type: 'number',
      valueFormatter: tons,
    },
    {
      field: 'actual_volume',
      headerName: 'Actual',
      width: 100,
      type: 'number',
      valueFormatter: tons,
    },
    {
      field: 'elapsed_pct',
      headerName: 'Elapsed',
      width: 90,
      type: 'number',
      valueFormatter: pctFmt,
    },
    {
      field: 'contracted_gp',
      headerName: 'Contracted GP',
      width: 130,
      type: 'number',
      valueFormatter: money,
    },
    { field: 'contract_end', headerName: 'Ends', width: 110 },
  ]

  const single = statuses.length === 1
  const label = single ? riskLabel(statuses[0]) : statuses.map(riskLabel).join(' / ')

  return (
    <Box>
      <PageHeader
        eyebrow="Overview"
        title={`${label} contracts`}
        subtitle="Every bid line currently at this status, scoped to what you can see. Open the customer to work the detail."
        actions={
          <Button
            component={RouterLink}
            to="/"
            variant="outlined"
            startIcon={<ArrowBackRoundedIcon />}
          >
            Back to overview
          </Button>
        }
      />
      <WorkspacePanel
        title="Bid lines"
        subtitle="Click a row to open the customer account behind the line."
        action={
          <Stack direction="row" spacing={0.75}>
            {statuses.map((s) => (
              <Chip key={s} label={riskLabel(s)} color={riskChipColor(s)} />
            ))}
          </Stack>
        }
      >
        {!known ? (
          <Box sx={{ py: 4 }}>Unknown risk status "{status}".</Box>
        ) : (
          <div style={{ height: 560, width: '100%' }}>
            <DataGrid
              rows={lines.data ?? []}
              columns={cols}
              getRowId={(r) => r.bid_line_id}
              loading={lines.isLoading}
              onRowClick={(p) => {
                const cgn = (p.row as RiskLine).customer_group_number
                if (cgn) navigate(`/accounts/${encodeURIComponent(cgn)}`)
              }}
            />
          </div>
        )}
      </WorkspacePanel>
    </Box>
  )
}
