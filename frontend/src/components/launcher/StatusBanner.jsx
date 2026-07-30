import Box from '@mui/material/Box'
import IconButton from '@mui/material/IconButton'
import Typography from '@mui/material/Typography'
import { colors } from '../../theme'

/**
 * Single dismissible launcher status strip (#119).
 * Persist until X — not a notification inbox.
 */
export default function StatusBanner({ message, tone = 'error', onDismiss }) {
  if (!message) return null

  const borderColor = tone === 'warning' ? colors.caution : '#EF5350'
  const textColor = tone === 'warning' ? colors.caution : colors.textPrimary

  return (
    <Box
      role="alert"
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 1,
        mx: 0.5,
        mb: 1,
        px: 1.25,
        py: 0.85,
        borderRadius: 1.5,
        border: `1px solid ${borderColor}`,
        bgcolor: colors.surface,
      }}
    >
      <Typography
        variant="body2"
        sx={{ flex: 1, color: textColor, m: 0, lineHeight: 1.35 }}
      >
        {message}
      </Typography>
      <IconButton
        size="small"
        aria-label="Dismiss"
        onClick={onDismiss}
        sx={{
          color: colors.textSecondary,
          p: 0.25,
          mt: -0.25,
          '&:hover': { color: colors.textPrimary, bgcolor: colors.hover },
        }}
      >
        <Box component="span" aria-hidden sx={{ fontSize: '1rem', lineHeight: 1 }}>
          ×
        </Box>
      </IconButton>
    </Box>
  )
}
