import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { colors } from '../../theme'

const DEFAULT_STATUS = [
  { label: 'Indexed', value: '—' },
  {
    label: 'Semantic Search',
    value: 'Disabled',
    tone: 'off',
    title: 'Semantic search is not ready',
  },
  {
    label: 'AI',
    value: 'Offline',
    tone: 'degraded',
    title: 'Local AI answers ship in v1.1',
  },
]

const DEFAULT_SHORTCUTS = [
  { keys: 'Alt+Space', action: 'Toggle' },
  { keys: 'Esc', action: 'Dismiss' },
]

const TONE_COLOR = {
  on: colors.accentGreen,
  degraded: colors.caution,
  off: colors.textSecondary,
}

/**
 * Launcher chrome: capability lights + keyboard hints (#120).
 * Explanations live in aria-label (no native white tooltips / help cursor).
 */
export default function Footer({
  status = DEFAULT_STATUS,
  shortcuts = DEFAULT_SHORTCUTS,
}) {
  return (
    <Box
      component="footer"
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 1.5,
        flexWrap: 'nowrap',
        px: 2.5,
        py: 0.85,
        borderTop: `1px solid ${colors.border}`,
        bgcolor: colors.surface,
        minHeight: 36,
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'nowrap',
          gap: 2,
          minWidth: 0,
          overflow: 'hidden',
        }}
      >
        {status.map((item) => {
          const tone = item.tone
          const valueColor = tone ? TONE_COLOR[tone] || colors.textPrimary : colors.textPrimary
          const ariaLabel = item.ariaLabel || (
            item.title
              ? `${item.label}: ${item.value}. ${item.title}`
              : undefined
          )
          return (
            <Typography
              key={item.label}
              variant="caption"
              aria-label={ariaLabel}
              sx={{
                color: colors.textSecondary,
                whiteSpace: 'nowrap',
              }}
            >
              <Box component="span" sx={{ color: colors.textSecondary, opacity: 0.75 }}>
                {item.label}:
              </Box>{' '}
              {tone ? (
                <Box
                  component="span"
                  aria-hidden
                  sx={{
                    display: 'inline-block',
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    bgcolor: valueColor,
                    mr: 0.55,
                    verticalAlign: 'middle',
                    mb: '1px',
                  }}
                />
              ) : null}
              <Box component="span" sx={{ color: valueColor, opacity: 0.95 }}>
                {item.value}
              </Box>
            </Typography>
          )
        })}
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexWrap: 'nowrap',
          gap: 1.5,
          flexShrink: 0,
        }}
      >
        {shortcuts.map((item) => (
          <Typography key={item.keys} variant="caption" sx={{ color: colors.textSecondary }}>
            <Box
              component="kbd"
              sx={{
                fontFamily: 'inherit',
                color: colors.textPrimary,
                opacity: 0.85,
                px: 0.55,
                py: 0.1,
                borderRadius: 0.75,
                border: `1px solid ${colors.border}`,
                bgcolor: colors.hover,
                fontSize: '0.68rem',
                mr: 0.5,
              }}
            >
              {item.keys}
            </Box>
            {item.action}
          </Typography>
        ))}
      </Box>
    </Box>
  )
}
