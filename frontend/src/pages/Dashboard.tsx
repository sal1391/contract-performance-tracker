import { Box, Chip, Grid, Paper, Stack, Typography } from '@mui/material'
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../api'
import { RISK_LABELS as LABELS, RISK_ORDER, RISK_TONES as TONES } from '../risk'
import { PageHeader, SummaryStrip, WorkspacePanel } from '../ui/layout'

type Summary = { by_status: Record<string, number>; gp_at_risk: number }

export default function Dashboard() {
  const api = useApi()
  const navigate = useNavigate()
  const openRisk = (status: string) => navigate(`/risk/${status}`)
  const { data, isLoading, error } = useQuery<Summary>({
    queryKey: ['dashboard-summary'],
    queryFn: async () => (await api.get('/dashboard/summary')).data,
  })

  if (isLoading) return <Typography>Loading dashboard...</Typography>
  if (error) return <Typography color="error">Could not load dashboard (is the API running?)</Typography>

  const byStatus = data?.by_status ?? {}
  const atRisk = byStatus.AT_RISK ?? 0
  const watch = byStatus.WATCH ?? 0
  const onTrack = byStatus.ON_TRACK ?? 0
  const ahead = byStatus.AHEAD ?? 0
  const complete = byStatus.COMPLETE ?? 0

  const queue = [
    {
      title: 'Immediate exposure',
      body: atRisk
        ? `${atRisk} contracts are carrying direct gross-profit risk right now.`
        : 'No contracts are currently carrying direct gross-profit risk.',
      count: atRisk,
      tone: 'danger' as const,
      status: 'AT_RISK',
    },
    {
      title: 'Needs review',
      body: watch
        ? `${watch} contracts are stable enough to stay open, but still need operator review.`
        : 'Nothing is sitting in the watch queue right now.',
      count: watch,
      tone: 'warm' as const,
      status: 'WATCH',
    },
    {
      title: 'Stable pipeline',
      body: `${onTrack + ahead + complete} contracts are moving through the expected operating flow.`,
      count: onTrack + ahead + complete,
      tone: 'primary' as const,
      status: 'ON_TRACK,AHEAD,COMPLETE',
    },
  ]

  return (
    <Box>
      <PageHeader
        eyebrow="Overview"
        title="Contract performance"
        subtitle="Risk first, movement second, and customer context one click away."
        actions={<Chip label="Today / this week" variant="outlined" />}
      />
      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, xl: 7 }}>
          <WorkspacePanel
            title="Risk posture"
            subtitle="Lead with the commercial exposure, then scan the current mix by operating status."
            minHeight="100%"
          >
            <Stack spacing={2.25}>
              <Paper
                sx={{
                  p: 3.5,
                  borderRadius: 4,
                  bgcolor: 'primary.dark',
                  color: 'primary.contrastText',
                }}
              >
                <Typography variant="overline" sx={{ color: 'inherit' }}>
                  Gross profit at risk
                </Typography>
                <Typography
                  sx={{
                    mt: 0.75,
                    fontSize: { xs: '2.5rem', md: '3.25rem' },
                    fontWeight: 700,
                    lineHeight: 1,
                  }}
                >
                  ${Math.round(data?.gp_at_risk ?? 0).toLocaleString()}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ mt: 1.25, color: 'rgba(255,255,255,0.72)', maxWidth: 540 }}
                >
                  This overview stays compact on purpose: the dashboard should orient the team in
                  seconds, then send them into Workbench for the line-level decision.
                </Typography>
              </Paper>
              <SummaryStrip
                items={RISK_ORDER.map((status) => ({
                  label: LABELS[status],
                  value: byStatus[status] ?? 0,
                  tone: TONES[status],
                  onClick: () => openRisk(status),
                }))}
              />
            </Stack>
          </WorkspacePanel>
        </Grid>
        <Grid size={{ xs: 12, xl: 5 }}>
          <WorkspacePanel
            title="Attention queue"
            subtitle="Use this as the first review pass before moving deeper into the contract stack."
            minHeight="100%"
          >
            <Stack spacing={1.25}>
              {queue.map((item) => (
                <Paper
                  key={item.title}
                  component="button"
                  onClick={() => openRisk(item.status)}
                  sx={{
                    p: 2,
                    width: '100%',
                    textAlign: 'left',
                    border: 'none',
                    cursor: 'pointer',
                    borderRadius: 3.5,
                    transition: 'transform 120ms ease, box-shadow 120ms ease',
                    '&:hover': { transform: 'translateY(-2px)', boxShadow: 4 },
                    bgcolor:
                      item.tone === 'danger'
                        ? 'rgba(197,95,67,0.08)'
                        : item.tone === 'warm'
                          ? 'rgba(181,122,69,0.1)'
                          : 'rgba(11,79,92,0.06)',
                  }}
                >
                  <Stack
                    direction={{ xs: 'column', sm: 'row' }}
                    spacing={1.5}
                    sx={{ justifyContent: 'space-between', alignItems: 'flex-start' }}
                  >
                    <Box>
                      <Typography variant="h6">{item.title}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>
                        {item.body}
                      </Typography>
                    </Box>
                    <Typography
                      sx={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1, flexShrink: 0 }}
                    >
                      {item.count}
                    </Typography>
                  </Stack>
                </Paper>
              ))}
            </Stack>
          </WorkspacePanel>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <WorkspacePanel
            title="Status signal"
            subtitle="A fast read on the contract mix without turning the overview into a wall of equal-weight cards."
          >
            <Stack spacing={1.25}>
              {RISK_ORDER.map((status) => (
                <Stack
                  key={status}
                  component="button"
                  onClick={() => openRisk(status)}
                  direction="row"
                  spacing={1.5}
                  sx={{
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    py: 0.75,
                    px: 1,
                    width: '100%',
                    border: 'none',
                    bgcolor: 'transparent',
                    cursor: 'pointer',
                    borderRadius: 2,
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <Typography variant="body1">{LABELS[status]}</Typography>
                  <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
                    <Chip
                      label={`${byStatus[status] ?? 0} contracts`}
                      color={
                        status === 'AT_RISK'
                          ? 'error'
                          : status === 'AHEAD'
                            ? 'success'
                            : status === 'WATCH'
                              ? 'warning'
                              : 'default'
                      }
                      variant={status === 'ON_TRACK' || status === 'COMPLETE' ? 'outlined' : 'filled'}
                    />
                    <ChevronRightRoundedIcon fontSize="small" sx={{ color: 'text.disabled' }} />
                  </Stack>
                </Stack>
              ))}
            </Stack>
          </WorkspacePanel>
        </Grid>
      </Grid>
    </Box>
  )
}
