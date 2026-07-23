import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { colors } from '../../theme'

const DEFAULT_STATUS = [
  { label: 'Indexed', value: '—' },
  { label: 'Semantic Search', value: 'Disabled' },
  { label: 'AI', value: 'Offline' },
]

const DEFAULT_SHORTCUTS = [
  { keys: 'Alt+Space', action: 'Toggle' },
  { keys: 'Esc', action: 'Dismiss' },
]

/**
 * Launcher chrome: capability/status stubs + keyboard hints.
 * Values will become live as indexer / AI land.
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
        {status.map((item) => (
          <Typography key={item.label} variant="caption" sx={{ color: colors.textSecondary }}>
            <Box component="span" sx={{ color: colors.textSecondary, opacity: 0.75 }}>
              {item.label}:
            </Box>{' '}
            <Box component="span" sx={{ color: colors.textPrimary, opacity: 0.9 }}>
              {item.value}
            </Box>
          </Typography>
        ))}
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
