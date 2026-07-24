import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { colors } from '../../theme'

/**
 * Flat Spotlight-style filename hits (#43 / #44).
 * Click or Enter (from SearchBar) opens via parent onActivate.
 */
export default function ResultsList({
  hits,
  selectedIndex = 0,
  onActivate,
}) {
  if (!hits?.length) return null

  return (
    <Box
      component="ul"
      role="listbox"
      aria-label="Search results"
      sx={{
        listStyle: 'none',
        m: 0,
        p: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 0.25,
      }}
    >
      {hits.map((hit, index) => {
        const selected = index === selectedIndex
        return (
          <Box
            component="li"
            key={hit.id ?? hit.path}
            role="option"
            aria-selected={selected}
            onClick={() => onActivate?.(hit, index)}
            sx={{
              px: 1.5,
              py: 1,
              borderRadius: 1.5,
              borderLeft: selected
                ? `2px solid ${colors.accent}`
                : '2px solid transparent',
              bgcolor: selected ? colors.hover : 'transparent',
              transition: 'background-color 120ms ease, border-color 120ms ease',
              cursor: 'pointer',
              '&:hover': {
                bgcolor: colors.hover,
              },
            }}
          >
            <Typography
              variant="body1"
              sx={{
                color: colors.textPrimary,
                fontWeight: 500,
                fontSize: '0.9375rem',
                lineHeight: 1.35,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {hit.name}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: colors.textSecondary,
                display: 'block',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                mt: 0.25,
              }}
            >
              {hit.path}
            </Typography>
          </Box>
        )
      })}
    </Box>
  )
}
