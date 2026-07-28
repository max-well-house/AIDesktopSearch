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
  degraded: '#EAB308',
  off: colors.textSecondary,
}

/**
 * Launcher chrome: capability lights + keyboard hints (#120).
 * Indexed stays plain text; Semantic/AI use tone + hover explanation.
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
        gap: 2,
        flexWrap: 'wrap',
        px: 2.5,
        py: 1.25,
        borderTop: `1px solid ${colors.border}`,
        bgcolor: colors.surface,
        minHeight: 44,
      }}
    >
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: { xs: 1.5, sm: 2.5 } }}>
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
              title={item.title || undefined}
              aria-label={ariaLabel}
              sx={{
                color: colors.textSecondary,
                cursor: item.title ? 'help' : undefined,
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
                    mr: 0.6,
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

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        {shortcuts.map((item) => (
          <Typography key={item.keys} variant="caption" sx={{ color: colors.textSecondary }}>
            <Box
              component="kbd"
              sx={{
                fontFamily: 'inherit',
                color: colors.textPrimary,
                opacity: 0.85,
                px: 0.6,
                py: 0.15,
                borderRadius: 0.75,
                border: `1px solid ${colors.border}`,
                bgcolor: colors.hover,
                fontSize: '0.7rem',
                mr: 0.6,
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
