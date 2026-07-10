import type { ReactNode } from 'react'
import { alpha, Box, ButtonBase, Paper, Stack, Typography, useTheme } from '@mui/material'
import { NavLink, useLocation } from 'react-router-dom'

export type AppShellNavItem = {
  to: string
  label: string
  icon: ReactNode
}

type AppShellProps = {
  brand: string
  navItems: AppShellNavItem[]
  utility?: ReactNode
  children: ReactNode
}

type PageHeaderProps = {
  eyebrow?: string
  title: string
  subtitle: string
  actions?: ReactNode
}

type WorkspacePanelProps = {
  title?: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
  minHeight?: number | string
}

type SummaryItem = {
  label: string
  value: ReactNode
  tone?: 'neutral' | 'primary' | 'warm' | 'danger' | 'success'
  onClick?: () => void
}

export function AppShell({ brand, navItems, utility, children }: AppShellProps) {
  const theme = useTheme()
  const location = useLocation()

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        maxWidth: 1720,
        mx: 'auto',
        width: '100%',
        px: { xs: 1.5, md: 2.5 },
        py: { xs: 1.5, md: 2.25 },
        gap: { xs: 1.5, md: 2.25 },
      }}
    >
      <Box
        component="nav"
        role="navigation"
        sx={{
          display: { xs: 'none', md: 'flex' },
          width: 124,
          flexShrink: 0,
        }}
      >
        <Paper
          sx={{
            width: '100%',
            borderRadius: 8,
            px: 1.5,
            py: 2.25,
            display: 'flex',
            flexDirection: 'column',
            gap: 1.25,
            bgcolor: theme.palette.primary.dark,
            color: theme.palette.primary.contrastText,
            borderColor: alpha('#ffffff', 0.08),
          }}
        >
          <Stack spacing={0.5} sx={{ px: 1, pb: 2.5 }}>
            <Typography variant="overline" sx={{ color: alpha('#ffffff', 0.64) }}>
              Triton
            </Typography>
            <Typography variant="h6" sx={{ lineHeight: 1.15, color: '#ffffff' }}>
              {brand}
            </Typography>
            <Typography variant="body2" sx={{ color: alpha('#ffffff', 0.66) }}>
              Operator workspace
            </Typography>
          </Stack>
          {navItems.map((item) => {
            const active =
              location.pathname === item.to ||
              (item.to !== '/' && location.pathname.startsWith(item.to))
            return (
              <ButtonBase
                key={item.to}
                component={NavLink}
                to={item.to}
                sx={{
                  width: '100%',
                  borderRadius: 4,
                  px: 1.25,
                  py: 1.35,
                  justifyContent: 'center',
                  color: active ? '#ffffff' : alpha('#ffffff', 0.72),
                  bgcolor: active ? alpha('#ffffff', 0.12) : 'transparent',
                  border: `1px solid ${active ? alpha('#ffffff', 0.14) : 'transparent'}`,
                }}
              >
                <Stack spacing={0.5} sx={{ alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>{item.icon}</Box>
                  <Typography variant="caption" sx={{ fontWeight: active ? 700 : 600 }}>
                    {item.label}
                  </Typography>
                </Stack>
              </ButtonBase>
            )
          })}
        </Paper>
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Paper
          sx={{
            minHeight: '100%',
            borderRadius: { xs: 5, md: 8 },
            overflow: 'hidden',
            bgcolor: alpha(theme.palette.background.paper, 0.96),
          }}
        >
          <Box
            sx={{
              px: { xs: 2, md: 3.5 },
              py: { xs: 1.75, md: 2.25 },
              borderBottom: `1px solid ${theme.palette.divider}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 2,
              flexWrap: 'wrap',
            }}
          >
            <Stack spacing={0.2}>
              <Typography variant="overline" color="secondary.main">
                Operator workspace
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Contract operating surface
              </Typography>
            </Stack>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1}
              sx={{ width: { xs: '100%', sm: 'auto' }, alignItems: { xs: 'stretch', sm: 'center' } }}
            >
              <Stack
                direction="row"
                spacing={1}
                sx={{ display: { xs: 'flex', md: 'none' }, overflowX: 'auto' }}
              >
                {navItems.map((item) => {
                  const active =
                    location.pathname === item.to ||
                    (item.to !== '/' && location.pathname.startsWith(item.to))
                  return (
                    <ButtonBase
                      key={item.to}
                      component={NavLink}
                      to={item.to}
                      sx={{
                        px: 1.5,
                        py: 0.9,
                        borderRadius: 999,
                        whiteSpace: 'nowrap',
                        border: `1px solid ${
                          active ? alpha(theme.palette.primary.main, 0.2) : theme.palette.divider
                        }`,
                        bgcolor: active ? alpha(theme.palette.primary.main, 0.08) : '#ffffff',
                        color: active ? 'primary.main' : 'text.secondary',
                      }}
                    >
                      <Typography variant="caption" sx={{ fontWeight: 700 }}>
                        {item.label}
                      </Typography>
                    </ButtonBase>
                  )
                })}
              </Stack>
              {utility}
            </Stack>
          </Box>
          <Box sx={{ p: { xs: 2, md: 3.5 }, minWidth: 0 }}>{children}</Box>
        </Paper>
      </Box>
    </Box>
  )
}

export function PageHeader({ eyebrow, title, subtitle, actions }: PageHeaderProps) {
  return (
    <Paper
      sx={{
        mb: 3,
        px: { xs: 2.25, md: 3 },
        py: { xs: 2.25, md: 2.8 },
        borderRadius: 6,
        bgcolor: alpha('#ffffff', 0.96),
      }}
    >
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={2}
        sx={{ justifyContent: 'space-between', alignItems: { xs: 'flex-start', md: 'center' } }}
      >
        <Stack spacing={0.75} sx={{ maxWidth: 760 }}>
          {eyebrow && (
            <Typography variant="overline" color="secondary.main">
              {eyebrow}
            </Typography>
          )}
          <Typography variant="h4">{title}</Typography>
          <Typography variant="body1" color="text.secondary">
            {subtitle}
          </Typography>
        </Stack>
        {actions}
      </Stack>
    </Paper>
  )
}

export function WorkspacePanel({
  title,
  subtitle,
  action,
  children,
  minHeight,
}: WorkspacePanelProps) {
  return (
    <Paper sx={{ borderRadius: 6, p: 2.25, minHeight, bgcolor: alpha('#ffffff', 0.98) }}>
      {(title || subtitle || action) && (
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1.5}
          sx={{ mb: 2, justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' } }}
        >
          <Stack spacing={0.25}>
            {title && <Typography variant="h6">{title}</Typography>}
            {subtitle && (
              <Typography variant="body2" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Stack>
          {action}
        </Stack>
      )}
      {children}
    </Paper>
  )
}

export function SummaryStrip({ items }: { items: SummaryItem[] }) {
  const theme = useTheme()

  const toneStyles: Record<NonNullable<SummaryItem['tone']>, { bg: string; fg: string }> = {
    neutral: {
      bg: alpha(theme.palette.primary.main, 0.04),
      fg: theme.palette.text.primary,
    },
    primary: {
      bg: alpha(theme.palette.primary.main, 0.08),
      fg: theme.palette.primary.main,
    },
    warm: {
      bg: alpha(theme.palette.secondary.main, 0.1),
      fg: theme.palette.secondary.main,
    },
    danger: {
      bg: alpha(theme.palette.error.main, 0.1),
      fg: theme.palette.error.main,
    },
    success: {
      bg: alpha(theme.palette.success.main, 0.1),
      fg: theme.palette.success.main,
    },
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gap: 1.5,
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      }}
    >
      {items.map((item) => {
        const tone = toneStyles[item.tone ?? 'neutral']
        return (
          <Paper
            key={item.label}
            {...(item.onClick
              ? {
                  component: ButtonBase,
                  onClick: item.onClick,
                  focusRipple: true,
                }
              : {})}
            sx={{
              p: 2.4,
              minHeight: 118,
              borderRadius: 3.5,
              bgcolor: tone.bg,
              borderColor: alpha(tone.fg, 0.12),
              overflow: 'hidden',
              ...(item.onClick
                ? {
                    width: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'transform 120ms ease, box-shadow 120ms ease',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: 4,
                      borderColor: alpha(tone.fg, 0.32),
                    },
                  }
                : {}),
            }}
          >
            <Typography
              variant="overline"
              sx={{
                display: 'block',
                color: tone.fg,
                lineHeight: 1.35,
                letterSpacing: '0.08em',
                whiteSpace: 'normal',
                wordBreak: 'break-word',
              }}
            >
              {item.label}
            </Typography>
            <Typography
              sx={{
                mt: 1,
                color: tone.fg,
                fontSize: { xs: '1.9rem', md: '2.15rem' },
                fontWeight: 700,
                lineHeight: 1.08,
                letterSpacing: '-0.04em',
                wordBreak: 'break-word',
              }}
            >
              {item.value}
            </Typography>
          </Paper>
        )
      })}
    </Box>
  )
}

export function EmptyWorkspace({
  title,
  body,
  action,
}: {
  title: string
  body: string
  action?: ReactNode
}) {
  return (
    <Paper
      sx={{
        p: 4,
        borderRadius: 5,
        textAlign: 'center',
        bgcolor: alpha('#ffffff', 0.72),
        borderStyle: 'dashed',
      }}
    >
      <Stack spacing={1.5} sx={{ alignItems: 'center' }}>
        <Typography variant="h6">{title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 420 }}>
          {body}
        </Typography>
        {action}
      </Stack>
    </Paper>
  )
}
