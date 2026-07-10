import { useMemo, useState } from 'react'
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { DataGrid, type GridColDef } from '@mui/x-data-grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApi } from '../api'

type Opt = { value: string; label: string | null }

const optLabel = (o: Opt) => (o.label && o.label !== o.value ? `${o.value} - ${o.label}` : o.value)
const num = (v: string) => (v !== '' && v != null ? Number(v) : null)
const s = (v: any) => (v == null ? '' : String(v))
const money2 = (v: any) => (v == null || v === '' ? '' : Number(v).toFixed(2))
const pct = (v: any) => (v == null || v === '' ? '' : `+/-${Math.round(Number(v) * 10000) / 100}%`)

export default function Workbench() {
  const api = useApi()
  const qc = useQueryClient()
  const [selected, setSelected] = useState<string>('')
  const [search, setSearch] = useState('')
  const [bidOpen, setBidOpen] = useState(false)
  const [lineOpen, setLineOpen] = useState(false)
  const [editBidId, setEditBidId] = useState<string | null>(null)
  const [editLineId, setEditLineId] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<{ kind: 'bid' | 'line'; id: string; label: string } | null>(
    null,
  )

  const get = (url: string, params?: any) => async () => (await api.get(url, { params })).data
  const contracts = useQuery<any[]>({
    queryKey: ['contracts', search],
    queryFn: get('/contracts', { q: search || undefined }),
  })
  const customers = useQuery<Opt[]>({
    queryKey: ['dim', 'customers'],
    queryFn: get('/dimensions/customers'),
  })
  const ports = useQuery<Opt[]>({ queryKey: ['dim', 'ports'], queryFn: get('/dimensions/ports') })
  const grades = useQuery<Opt[]>({ queryKey: ['dim', 'grades'], queryFn: get('/dimensions/grades') })
  const suppliers = useQuery<Opt[]>({
    queryKey: ['dim', 'suppliers'],
    queryFn: get('/dimensions/suppliers'),
  })
  const indexes = useQuery<Opt[]>({
    queryKey: ['dim', 'indexes'],
    queryFn: get('/dimensions/indexes'),
  })
  const lookups = useQuery<any>({ queryKey: ['lookups'], queryFn: get('/dimensions/lookups') })
  const offices = useQuery<any[]>({
    queryKey: ['org-offices'],
    queryFn: get('/org/offices'),
    retry: false,
  })
  const brokers = useQuery<any[]>({
    queryKey: ['brokers'],
    queryFn: get('/org/brokers'),
    retry: false,
  })
  const brokerName = useMemo(() => {
    const map = new Map<string, string>()
    ;(brokers.data ?? []).forEach((b) => map.set(b.id, b.display_name ?? b.email))
    return (id: string | null) => (id ? map.get(id) ?? '' : '')
  }, [brokers.data])
  const lines = useQuery<any[]>({
    queryKey: ['bid-lines', selected],
    queryFn: get('/bid-lines', { contract_id: selected }),
    enabled: Boolean(selected),
  })

  const emptyBid = {
    contract_source_id: '',
    customer_group_number: '',
    bid_year: '2026',
    region: '',
    source_status: '',
    bid_sub_note: '',
    office_id: '',
  }
  const emptyStarterLine = {
    port: '',
    grade: '',
    supplier_number: '',
    contracted_volume: '',
    bid_status: '',
  }
  const [bid, setBid] = useState<any>(emptyBid)
  const [starterLine, setStarterLine] = useState<any>(emptyStarterLine)
  const starterLineHasValues = Object.values(starterLine).some(
    (value) => String(value ?? '').trim() !== '',
  )

  const openNewBid = () => {
    setBid(emptyBid)
    setStarterLine(emptyStarterLine)
    setEditBidId(null)
    setBidOpen(true)
  }

  const openEditBid = (row: any) => {
    setBid({
      contract_source_id: s(row.contract_source_id),
      customer_group_number: s(row.customer_group_number),
      bid_year: s(row.bid_year),
      region: s(row.region),
      source_status: s(row.source_status),
      bid_sub_note: s(row.bid_sub_note),
      office_id: s(row.office_id),
    })
    setStarterLine(emptyStarterLine)
    setEditBidId(row.id)
    setBidOpen(true)
  }

  const saveBid = useMutation({
    mutationFn: async () => {
      const contractBody = {
        contract_source_id: bid.contract_source_id,
        customer_group_number: bid.customer_group_number,
        customer_group_name:
          customers.data?.find((c) => c.value === bid.customer_group_number)?.label ?? null,
        bid_year: num(bid.bid_year),
        region: bid.region || null,
        source_status: bid.source_status || null,
        bid_sub_note: bid.bid_sub_note || null,
        office_id: bid.office_id || null,
      }

      if (editBidId) return (await api.patch(`/contracts/${editBidId}`, contractBody)).data

      const created = (await api.post('/contracts', contractBody)).data
      if (starterLineHasValues) {
        await api.post('/bid-lines', {
          contract_id: created.id,
          port: starterLine.port,
          grade: starterLine.grade || null,
          supplier_number: starterLine.supplier_number || null,
          supplier_name:
            suppliers.data?.find((supplier) => supplier.value === starterLine.supplier_number)
              ?.label ?? null,
          contracted_volume: num(starterLine.contracted_volume),
          bid_status: starterLine.bid_status || null,
        })
      }
      return created
    },
    onSuccess: (created: any) => {
      qc.invalidateQueries({ queryKey: ['contracts'] })
      if (!editBidId) {
        setSelected(created.id)
        qc.invalidateQueries({ queryKey: ['bid-lines', created.id] })
      }
      setBidOpen(false)
      setBid(emptyBid)
      setStarterLine(emptyStarterLine)
      setEditBidId(null)
    },
  })

  const emptyLine: any = {
    port: '',
    grade: '',
    supplier_number: '',
    index_symbol: '',
    formula: '',
    price_uom: 'MT',
    selling_premium: '',
    buying_premium: '',
    freight_type: '',
    pricing_days: '',
    supplier_terms: '',
    contracted_volume: '',
    volume_tolerance: '',
    tolerance_pct: '',
    supply_method: '',
    spec: '',
    contract_start: '',
    contract_end: '',
    date_offered: '',
    freight_fee: '',
    notes: '',
    bid_notes: '',
    bid_status: '',
    owner_user_id: '',
  }
  const [line, setLine] = useState<any>(emptyLine)

  const openNewLine = () => {
    setLine(emptyLine)
    setEditLineId(null)
    setLineOpen(true)
  }

  const openEditLine = (row: any) => {
    const mapped = Object.fromEntries(Object.keys(emptyLine).map((key) => [key, s(row[key])]))
    mapped.tolerance_pct =
      row.tolerance_pct != null ? String(Math.round(row.tolerance_pct * 10000) / 100) : ''
    setLine(mapped)
    setEditLineId(row.id)
    setLineOpen(true)
  }

  const saveLine = useMutation({
    mutationFn: async () => {
      const body = {
        port: line.port,
        grade: line.grade || null,
        supplier_number: line.supplier_number || null,
        supplier_name:
          suppliers.data?.find((supplier) => supplier.value === line.supplier_number)?.label ??
          null,
        index_symbol: line.index_symbol || null,
        formula: line.formula || null,
        price_uom: line.price_uom || null,
        selling_premium: num(line.selling_premium),
        buying_premium: num(line.buying_premium),
        freight_type: line.freight_type || null,
        pricing_days: line.pricing_days || null,
        supplier_terms: line.supplier_terms || null,
        contracted_volume: num(line.contracted_volume),
        volume_tolerance: line.volume_tolerance || null,
        tolerance_pct:
          line.tolerance_pct !== '' && line.tolerance_pct != null
            ? Number(line.tolerance_pct) / 100
            : null,
        supply_method: line.supply_method || null,
        spec: line.spec || null,
        contract_start: line.contract_start || null,
        contract_end: line.contract_end || null,
        date_offered: line.date_offered || null,
        freight_fee: line.freight_fee || null,
        notes: line.notes || null,
        bid_notes: line.bid_notes || null,
        bid_status: line.bid_status || null,
        owner_user_id: line.owner_user_id || null,
      }

      return editLineId
        ? (await api.patch(`/bid-lines/${editLineId}`, body)).data
        : (await api.post('/bid-lines', { ...body, contract_id: selected })).data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bid-lines', selected] })
      setLineOpen(false)
      setLine(emptyLine)
      setEditLineId(null)
    },
  })

  const deleteBid = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/contracts/${id}`)).data,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['contracts'] })
      if (selected === id) setSelected('')
    },
  })

  const deleteLine = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/bid-lines/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bid-lines', selected] }),
  })

  const runDelete = () => {
    if (!confirm) return
    if (confirm.kind === 'bid') deleteBid.mutate(confirm.id)
    else deleteLine.mutate(confirm.id)
    setConfirm(null)
  }

  const txt = (label: string, field: string, extra: any = {}) => (
    <TextField
      fullWidth
      size="small"
      label={label}
      value={line[field]}
      onChange={(e) => setLine({ ...line, [field]: e.target.value })}
      {...extra}
    />
  )

  const sel = (label: string, field: string, options?: Opt[]) => (
    <TextField
      select
      fullWidth
      size="small"
      label={label}
      value={line[field]}
      onChange={(e) => setLine({ ...line, [field]: e.target.value })}
    >
      <MenuItem value="">-</MenuItem>
      {(options ?? []).map((option) => (
        <MenuItem key={option.value} value={option.value}>
          {optLabel(option)}
        </MenuItem>
      ))}
    </TextField>
  )

  const onIndexChange = (symbol: string) =>
    setLine((prev: any) => ({
      ...prev,
      index_symbol: symbol,
      formula: !prev.formula || prev.formula === prev.index_symbol ? symbol : prev.formula,
    }))

  const dateProps = { type: 'date', slotProps: { inputLabel: { shrink: true } } }

  const editCol = (handler: (row: any) => void): GridColDef => ({
    field: 'edit',
    headerName: '',
    width: 64,
    sortable: false,
    renderCell: (params) => (
      <Button
        size="small"
        onClick={(e) => {
          e.stopPropagation()
          handler(params.row)
        }}
      >
        Edit
      </Button>
    ),
  })

  const delCol = (kind: 'bid' | 'line', label: (row: any) => string): GridColDef => ({
    field: 'del',
    headerName: '',
    width: 78,
    sortable: false,
    renderCell: (params) => (
      <Button
        size="small"
        color="error"
        onClick={(e) => {
          e.stopPropagation()
          setConfirm({ kind, id: params.row.id, label: label(params.row) })
        }}
      >
        Delete
      </Button>
    ),
  })

  const contractCols: GridColDef[] = [
    { field: 'contract_source_id', headerName: 'QB ID', width: 100 },
    { field: 'customer_group_name', headerName: 'Customer', width: 150 },
    { field: 'bid_year', headerName: 'Year', width: 70 },
    { field: 'region', headerName: 'Region', width: 110 },
    { field: 'source_status', headerName: 'QB Status', width: 110 },
    { field: 'bid_sub_note', headerName: 'Bid sub note', width: 180 },
    editCol(openEditBid),
    delCol('bid', (row) => `${row.contract_source_id} - ${row.customer_group_name ?? ''}`),
  ]

  const lineCols: GridColDef[] = [
    editCol(openEditLine),
    { field: 'port', headerName: 'Port', width: 100 },
    { field: 'grade', headerName: 'Grade', width: 80 },
    { field: 'supplier_name', headerName: 'Supplier', width: 120 },
    {
      field: 'owner_user_id',
      headerName: 'Broker',
      width: 130,
      valueGetter: (value) => brokerName(value as string | null),
    },
    { field: 'index_symbol', headerName: 'Index', width: 95 },
    { field: 'price_uom', headerName: 'UOM', width: 65 },
    {
      field: 'selling_premium',
      headerName: 'Sell',
      width: 70,
      type: 'number',
      valueFormatter: money2,
    },
    {
      field: 'buying_premium',
      headerName: 'Buy',
      width: 70,
      type: 'number',
      valueFormatter: money2,
    },
    { field: 'margin', headerName: 'Margin', width: 75, type: 'number', valueFormatter: money2 },
    { field: 'contracted_volume', headerName: 'Contracted', width: 100, type: 'number' },
    { field: 'tolerance_pct', headerName: 'Tol. +/-', width: 80, type: 'number', valueFormatter: pct },
    { field: 'gross_profit', headerName: 'Gross Profit', width: 110, type: 'number' },
    { field: 'supply_method', headerName: 'Supply', width: 85 },
    { field: 'supplier_terms', headerName: 'Terms', width: 85 },
    { field: 'spec', headerName: 'Spec', width: 100 },
    { field: 'contract_start', headerName: 'Start', width: 105 },
    { field: 'contract_end', headerName: 'End', width: 105 },
    { field: 'date_offered', headerName: 'Offered', width: 105 },
    { field: 'bid_status', headerName: 'Bid Status', width: 95 },
    delCol('line', (row) => `${row.port} - ${row.grade ?? ''} - ${row.supplier_name ?? ''}`),
  ]

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5">Bids / Contracts</Typography>
        <Button variant="contained" onClick={openNewBid}>
          + New Bid
        </Button>
      </Stack>
      <Typography variant="caption" color="text.secondary">
        In production, bids load from Snowflake (CONTRACT_INTAKE sync). <b>+ New Bid</b> is the
        manual entry path for local testing - these are saved as source "MANUAL".
      </Typography>
      <br />
      <TextField
        size="small"
        label="Search QB ID / customer"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mt: 1.5, width: 360 }}
      />

      <div style={{ height: 280, width: '100%', marginTop: 12 }}>
        <DataGrid
          rows={contracts.data ?? []}
          columns={contractCols}
          getRowId={(row) => row.id}
          loading={contracts.isLoading}
          onRowClick={(params) => setSelected(String(params.id))}
        />
      </div>

      {selected && (
        <Box sx={{ mt: 3 }}>
          <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Bid lines</Typography>
            <Button variant="outlined" onClick={openNewLine}>
              + Add line
            </Button>
          </Stack>
          <div style={{ height: 360, width: '100%', marginTop: 8 }}>
            <DataGrid
              rows={lines.data ?? []}
              columns={lineCols}
              getRowId={(row) => row.id}
              loading={lines.isLoading}
            />
          </div>
        </Box>
      )}

      <Dialog open={bidOpen} onClose={() => setBidOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editBidId ? 'Edit bid - QB header' : 'New bid - QB header'}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="QB ID"
              value={bid.contract_source_id}
              onChange={(e) => setBid({ ...bid, contract_source_id: e.target.value })}
            />
            <TextField
              select
              label="Client / Customer"
              value={bid.customer_group_number}
              onChange={(e) => setBid({ ...bid, customer_group_number: e.target.value })}
            >
              {(customers.data ?? []).map((customer) => (
                <MenuItem key={customer.value} value={customer.value}>
                  {optLabel(customer)}
                </MenuItem>
              ))}
            </TextField>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                fullWidth
                label="Bid year"
                value={bid.bid_year}
                onChange={(e) => setBid({ ...bid, bid_year: e.target.value })}
              />
              <TextField
                fullWidth
                label="Region"
                value={bid.region}
                onChange={(e) => setBid({ ...bid, region: e.target.value })}
              />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                fullWidth
                label="QB status"
                value={bid.source_status}
                onChange={(e) => setBid({ ...bid, source_status: e.target.value })}
              />
              <TextField
                select
                fullWidth
                label="Office (owns this bid)"
                value={bid.office_id}
                onChange={(e) => setBid({ ...bid, office_id: e.target.value })}
                helperText="Drives who can see it - defaults to your home office"
              >
                <MenuItem value="">- (use my home office)</MenuItem>
                {(offices.data ?? []).map((office) => (
                  <MenuItem key={office.id} value={office.id}>
                    {office.name}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <TextField
              label="Bid sub note"
              multiline
              minRows={2}
              value={bid.bid_sub_note}
              onChange={(e) => setBid({ ...bid, bid_sub_note: e.target.value })}
            />

            {!editBidId && (
              <>
                <Box sx={{ pt: 0.5 }}>
                  <Typography variant="overline" color="secondary.main">
                    Starter bid line
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>
                    Grade belongs to the line, not the header. Add the first line here so a new bid
                    does not open missing its core commercial fields.
                  </Typography>
                </Box>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <TextField
                    select
                    fullWidth
                    label="Port"
                    value={starterLine.port}
                    onChange={(e) => setStarterLine({ ...starterLine, port: e.target.value })}
                    helperText={
                      starterLineHasValues && !starterLine.port
                        ? 'Port is required when adding a starter line.'
                        : ' '
                    }
                  >
                    <MenuItem value="">Leave blank</MenuItem>
                    {(ports.data ?? []).map((port) => (
                      <MenuItem key={port.value} value={port.value}>
                        {optLabel(port)}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    fullWidth
                    label="Grade"
                    value={starterLine.grade}
                    onChange={(e) => setStarterLine({ ...starterLine, grade: e.target.value })}
                  >
                    <MenuItem value="">Leave blank</MenuItem>
                    {(grades.data ?? []).map((grade) => (
                      <MenuItem key={grade.value} value={grade.value}>
                        {optLabel(grade)}
                      </MenuItem>
                    ))}
                  </TextField>
                </Stack>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <TextField
                    select
                    fullWidth
                    label="Supplier"
                    value={starterLine.supplier_number}
                    onChange={(e) =>
                      setStarterLine({ ...starterLine, supplier_number: e.target.value })
                    }
                  >
                    <MenuItem value="">Leave blank</MenuItem>
                    {(suppliers.data ?? []).map((supplier) => (
                      <MenuItem key={supplier.value} value={supplier.value}>
                        {optLabel(supplier)}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    fullWidth
                    label="Contracted volume"
                    value={starterLine.contracted_volume}
                    onChange={(e) =>
                      setStarterLine({ ...starterLine, contracted_volume: e.target.value })
                    }
                  />
                </Stack>
                <TextField
                  select
                  fullWidth
                  label="Bid status"
                  value={starterLine.bid_status}
                  onChange={(e) => setStarterLine({ ...starterLine, bid_status: e.target.value })}
                >
                  <MenuItem value="">Leave blank</MenuItem>
                  {(lookups.data?.bid_status ?? []).map((option: Opt) => (
                    <MenuItem key={option.value} value={option.value}>
                      {optLabel(option)}
                    </MenuItem>
                  ))}
                </TextField>
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBidOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={
              !bid.contract_source_id ||
              !bid.customer_group_number ||
              saveBid.isPending ||
              (starterLineHasValues && !starterLine.port)
            }
            onClick={() => saveBid.mutate()}
          >
            {editBidId ? 'Save' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={lineOpen} onClose={() => setLineOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{editLineId ? 'Edit bid line' : 'Add bid line'}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              {sel('Port *', 'port', ports.data)}
              {sel('Grade', 'grade', grades.data)}
              {sel('Supplier', 'supplier_number', suppliers.data)}
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                select
                fullWidth
                size="small"
                label="Index"
                value={line.index_symbol}
                onChange={(e) => onIndexChange(e.target.value)}
              >
                <MenuItem value="">-</MenuItem>
                {(indexes.data ?? []).map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {optLabel(option)}
                  </MenuItem>
                ))}
              </TextField>
              {txt('Formula', 'formula', {
                helperText: 'Auto-filled from Index; edit to override',
              })}
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              {sel('Price UOM', 'price_uom', lookups.data?.price_uom)}
              {txt('Selling premium', 'selling_premium')}
              {txt('Buying premium', 'buying_premium')}
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              {sel('Freight', 'freight_type', lookups.data?.freight_type)}
              {sel('Pricing days', 'pricing_days', lookups.data?.pricing_days)}
              {txt('Supplier terms', 'supplier_terms')}
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              {txt('Contracted volume', 'contracted_volume')}
              {txt('Volume tolerance (note)', 'volume_tolerance')}
              {txt('Tol. +/- %', 'tolerance_pct', { type: 'number' })}
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              {sel('Supply method', 'supply_method', lookups.data?.supply_method)}
              {txt('Spec', 'spec')}
              {sel('Bid status', 'bid_status', lookups.data?.bid_status)}
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                select
                fullWidth
                size="small"
                label="Customer broker (who entered it)"
                value={line.owner_user_id}
                onChange={(e) => setLine({ ...line, owner_user_id: e.target.value })}
                helperText="Defaults to you; attribution only - does not change visibility"
              >
                <MenuItem value="">- (me)</MenuItem>
                {(brokers.data ?? []).map((broker: any) => (
                  <MenuItem key={broker.id} value={broker.id}>
                    {broker.display_name ?? broker.email}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              {txt('Contract start', 'contract_start', dateProps)}
              {txt('Contract end', 'contract_end', dateProps)}
              {txt('Date offered', 'date_offered', dateProps)}
            </Stack>
            {txt('Freight fee', 'freight_fee')}
            {txt('Notes', 'notes', { multiline: true, minRows: 2 })}
            {txt('Bid notes', 'bid_notes', { multiline: true, minRows: 2 })}
            <Typography variant="caption" color="text.secondary">
              Margin and Gross Profit are computed automatically from the premiums and volume.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLineOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!line.port || saveLine.isPending}
            onClick={() => saveLine.mutate()}
          >
            {editLineId ? 'Save' : 'Add line'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(confirm)} onClose={() => setConfirm(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Delete {confirm?.kind === 'bid' ? 'bid' : 'bid line'}?</DialogTitle>
        <DialogContent dividers>
          <Typography>{confirm?.label}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {confirm?.kind === 'bid'
              ? 'This permanently deletes the bid and all its bid lines and LIFT mappings.'
              : 'This permanently deletes the bid line and its LIFT mappings.'}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={runDelete}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
