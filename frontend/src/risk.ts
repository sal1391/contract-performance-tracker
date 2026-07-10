// Shared risk-status metadata used by the dashboard KPIs, the drill-down page, and the
// accounts view so the labels/colors stay consistent everywhere.

export const RISK_ORDER = ['AT_RISK', 'WATCH', 'ON_TRACK', 'AHEAD', 'COMPLETE'] as const
export type RiskStatus = (typeof RISK_ORDER)[number]

export const RISK_LABELS: Record<string, string> = {
  AT_RISK: 'At risk',
  WATCH: 'Watch',
  ON_TRACK: 'On track',
  AHEAD: 'Ahead',
  COMPLETE: 'Complete',
}

// SummaryStrip tone tokens (see ui/layout.tsx).
export const RISK_TONES: Record<string, 'danger' | 'warm' | 'primary' | 'success' | 'neutral'> = {
  AT_RISK: 'danger',
  WATCH: 'warm',
  ON_TRACK: 'primary',
  AHEAD: 'success',
  COMPLETE: 'neutral',
}

// MUI Chip color for a risk status.
export function riskChipColor(
  status: string | null | undefined,
): 'error' | 'warning' | 'info' | 'success' | 'default' {
  switch (status) {
    case 'AT_RISK':
      return 'error'
    case 'WATCH':
      return 'warning'
    case 'ON_TRACK':
      return 'info'
    case 'AHEAD':
      return 'success'
    default:
      return 'default'
  }
}

export const riskLabel = (status: string | null | undefined) =>
  status ? RISK_LABELS[status] ?? status : '-'
