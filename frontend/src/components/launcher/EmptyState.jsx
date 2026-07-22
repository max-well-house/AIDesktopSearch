import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { colors } from '../../theme'

/** Intentional idle guidance — not a "no results" dead end. */
export default function EmptyState() {
  return (
    <Box
      sx={{
        textAlign: 'center',
        px: 3,
        maxWidth: '28rem',
        mx: 'auto',
      }}
    >
      <Typography
        variant="body1"
        sx={{ color: colors.textPrimary, fontWeight: 500, mb: 1 }}
      >
        Start typing to search your files.
      </Typography>
      <Typography variant="body2" sx={{ color: colors.textSecondary, lineHeight: 1.55 }}>
        Search by filename, document contents, or ask a question in natural language.
      </Typography>
    </Box>
  )
}
