import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import { colors } from '../../theme'

/**
 * Intentional idle guidance — not a "no results" dead end.
 * Zero roots: tell the truth and offer Add folder (#146).
 */
export default function EmptyState({
  zeroRoots = false,
  addingFolder = false,
  onAddFolder,
  onOpenSettings,
}) {
  if (zeroRoots) {
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
          Add a folder to start searching.
        </Typography>
        <Typography variant="body2" sx={{ color: colors.textSecondary, lineHeight: 1.55, mb: 2 }}>
          Nothing is indexed until you choose a folder. Search stays empty without one.
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={() => onAddFolder?.()}
          disabled={addingFolder || !onAddFolder}
          sx={{ mb: onOpenSettings ? 1.5 : 0 }}
        >
          {addingFolder ? 'Adding…' : 'Add folder…'}
        </Button>
        {onOpenSettings ? (
          <Typography variant="body2" sx={{ color: colors.textSecondary }}>
            <Box
              component="button"
              type="button"
              onClick={onOpenSettings}
              sx={{
                border: 0,
                background: 'none',
                p: 0,
                m: 0,
                cursor: 'pointer',
                font: 'inherit',
                color: colors.accent,
                textDecoration: 'underline',
                textUnderlineOffset: '2px',
              }}
            >
              Open Settings
            </Box>
            {' '}
            to manage folders later.
          </Typography>
        ) : null}
      </Box>
    )
  }

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
        Search by filename, document contents, or meaning — then open the file.
      </Typography>
    </Box>
  )
}
