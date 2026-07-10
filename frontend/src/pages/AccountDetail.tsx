import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import {
  Box,
  Button,
  Chip,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink, useParams } from 'react-router-dom'
import { useApi } from '../api'
import { riskChipColor, riskLabel } from '../risk'
import { PageHeader, SummaryStrip, WorkspacePanel } from '../ui/layout'

type AccountLine = {
  id: string
  contract_id: string
  port: string
  grade: string | null
  supplier_name: string | null
  bid_status: string | null
  risk_status: string | null
  contracted_volume: number | null
  gross_profit: number | null
  margin: number | null
}

type AccountContract = {
  id: string
  contract_source_id: string
  bid_year: number | null
  region: string | null
  source_status: string | null
  risk_status: string | null
  lines: AccountLine[]
}

type AccountSummary = {
  customer_group_number: string
  customer_group_name: string | null
  contract_count: number
  line_count: number
  gp_won: number
  gp_pending: number
  gp_lost: number
  win_rate: number | null
  volume_won: number
  volume_pending: number
}

type AccountDetailData = {
  summary: AccountSummary
  contracts: AccountContract[]
}

const money = (value: number | null | undefined) =>
  value == null ? '-' : `$${Math.round(value).toLocaleString()}`
const tons = (value: number | null | undefined) =>
  value == null ? '-' : Math.round(value).toLocaleString()
const pct = (value: number | null | undefined) =>
  value == null ? '-' : `${Math.round(value * 100)}%`
const sumNumber = (values: Array<number | null | undefined>) =>
  values.reduce<number>((total, value) => total + (value ?? 0), 0)

function statusTone(status: string | null) {
  switch (status) {
    case 'WON':
      return 'success' as const
    case 'PENDING':
      return 'warning' as const
    case 'LOST':
      return 'error' as const
    default:
      return 'default' as const
  }
}

function ContractFact({ label, value }: { label: string; value: string }) {
  return (
    <Paper
      variant="outlined"
      sx={{
        px: 1.5,
        py: 1,
        minWidth: 108,
        borderRadius: 3,
        bgcolor: 'rgba(255,255,255,0.78)',
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.2, fontWeight: 700 }}>
        {value}
      </Typography>
    </Paper>
  )
}

export default function AccountDetail() {
  const api = useApi()
  const { customerGroupNumber } = useParams()

  const detail = useQuery<AccountDetailData>({
    queryKey: ['account-detail', customerGroupNumber],
    enabled: Boolean(customerGroupNumber),
    queryFn: async () =>
      (await api.get(`/accounts/${encodeURIComponent(customerGroupNumber ?? '')}`)).data,
  })

  if (!customerGroupNumber) {
    return <Typography color="error">Missing account id.</Typography>
  }

  if (detail.isLoading) {
    return <Typography>Loading account...</Typography>
  }

  if (detail.error || !detail.data) {
    return <Typography color="error">Could not load this account.</Typography>
  }

  const { summary, contracts } = detail.data
  const accountName = summary.customer_group_name ?? summary.customer_group_number

  return (
    <Box>
      <PageHeader
        eyebrow="Accounts"
        title={accountName}
        subtitle={`Customer group ${summary.customer_group_number} with ${summary.contract_count} visible contracts and ${summary.line_count} visible bid lines.`}
        actions={
          <Button
            component={RouterLink}
            to="/accounts"
            variant="outlined"
            startIcon={<ArrowBackRoundedIcon />}
          >
            Back to accounts
          </Button>
        }
      />

      <SummaryStrip
        items={[
          { label: 'Contracts', value: summary.contract_count, tone: 'primary' },
          { label: 'Bid lines', value: summary.line_count, tone: 'neutral' },
          { label: 'Win rate', value: pct(summary.win_rate), tone: 'success' },
          { label: 'GP won', value: money(summary.gp_won), tone: 'success' },
          { label: 'GP pending', value: money(summary.gp_pending), tone: 'warm' },
          { label: 'GP lost', value: money(summary.gp_lost), tone: 'danger' },
        ]}
      />

      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, lg: 4 }}>
          <WorkspacePanel
            title="Commercial picture"
            subtitle="Rollup across the lines visible to the current user."
            minHeight="100%"
          >
            <Stack spacing={1.25}>
              <Paper
                sx={{
                  p: 2.5,
                  borderRadius: 3.5,
                  bgcolor: 'primary.dark',
                  color: 'primary.contrastText',
                }}
              >
                <Typography variant="overline" sx={{ color: 'inherit' }}>
                  Pending volume
                </Typography>
                <Typography sx={{ mt: 0.75, fontSize: '2rem', fontWeight: 700, lineHeight: 1 }}>
                  {tons(summary.volume_pending)}
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, color: 'rgba(255,255,255,0.72)' }}>
                  Tons still sitting inside the active decision window.
                </Typography>
              </Paper>
              <Paper sx={{ p: 2.25, borderRadius: 3.5 }}>
                <Typography variant="overline" color="secondary.main">
                  Won volume
                </Typography>
                <Typography sx={{ mt: 0.75, fontSize: '1.6rem', fontWeight: 700 }}>
                  {tons(summary.volume_won)}
                </Typography>
              </Paper>
              <Paper sx={{ p: 2.25, borderRadius: 3.5 }}>
                <Typography variant="body2" color="text.secondary">
                  This view keeps the account summary and the contract detail together so the team
                  can move from customer context to line-level action without bouncing back to
                  overview.
                </Typography>
              </Paper>
            </Stack>
          </WorkspacePanel>
        </Grid>
        <Grid size={{ xs: 12, lg: 8 }}>
          <WorkspacePanel
            title="Contracts in this account"
            subtitle="Each contract keeps its bid lines attached so the jump from customer to execution stays short."
          >
            <Stack spacing={2}>
              {contracts.map((contract) => {
                const lineCount = contract.lines.length
                const totalVolume = sumNumber(contract.lines.map((line) => line.contracted_volume))
                const totalGrossProfit = sumNumber(contract.lines.map((line) => line.gross_profit))

                return (
                  <Paper key={contract.id} sx={{ p: 2.5, borderRadius: 3.5 }}>
                    <Stack
                      direction={{ xs: 'column', xl: 'row' }}
                      spacing={2}
                      sx={{
                        justifyContent: 'space-between',
                        alignItems: { xs: 'flex-start', xl: 'flex-start' },
                        mb: 2,
                      }}
                    >
                      <Stack spacing={0.45} sx={{ minWidth: 0 }}>
                        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                          <Typography variant="h6">{contract.contract_source_id}</Typography>
                          {contract.risk_status && (
                            <Chip
                              size="small"
                              label={riskLabel(contract.risk_status)}
                              color={riskChipColor(contract.risk_status)}
                            />
                          )}
                        </Stack>
                        <Typography variant="body2" color="text.secondary">
                          {(contract.region || 'Region not set') +
                            ' - ' +
                            (contract.bid_year || 'Year not set')}
                        </Typography>
                      </Stack>
                      <Stack
                        direction="row"
                        spacing={1}
                        useFlexGap
                        sx={{
                          width: '100%',
                          flexWrap: 'wrap',
                          justifyContent: { xs: 'flex-start', xl: 'flex-end' },
                        }}
                      >
                        <ContractFact
                          label="QB status"
                          value={contract.source_status || 'No QB status'}
                        />
                        <ContractFact
                          label="Bid lines"
                          value={`${lineCount} ${lineCount === 1 ? 'line' : 'lines'}`}
                        />
                        <ContractFact label="Volume" value={tons(totalVolume)} />
                        <ContractFact label="Gross profit" value={money(totalGrossProfit)} />
                      </Stack>
                    </Stack>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Port</TableCell>
                          <TableCell>Grade</TableCell>
                          <TableCell>Supplier</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Risk</TableCell>
                          <TableCell align="right">Volume</TableCell>
                          <TableCell align="right">Margin</TableCell>
                          <TableCell align="right">Gross profit</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {contract.lines.map((line) => (
                          <TableRow key={line.id}>
                            <TableCell>{line.port}</TableCell>
                            <TableCell>{line.grade || '-'}</TableCell>
                            <TableCell>{line.supplier_name || '-'}</TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                label={line.bid_status || 'OPEN'}
                                color={statusTone(line.bid_status)}
                              />
                            </TableCell>
                            <TableCell>
                              {line.risk_status ? (
                                <Chip
                                  size="small"
                                  variant="outlined"
                                  label={riskLabel(line.risk_status)}
                                  color={riskChipColor(line.risk_status)}
                                />
                              ) : (
                                '-'
                              )}
                            </TableCell>
                            <TableCell align="right">{tons(line.contracted_volume)}</TableCell>
                            <TableCell align="right">{money(line.margin)}</TableCell>
                            <TableCell align="right">{money(line.gross_profit)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Paper>
                )
              })}
            </Stack>
          </WorkspacePanel>
        </Grid>
      </Grid>
    </Box>
  )
}
