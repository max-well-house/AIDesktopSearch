import { useEffect, useRef } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { colors } from '../../theme'

export function resultOptionId(index) {
  return `search-result-${index}`
}

/**
 * Flat Spotlight-style filename hits (#43 / #44 / #83).
 * Click or Enter (from SearchBar) opens via parent onActivate.
 * Page caption only for PDF content hits (#57 / #62).
 */
export default function ResultsList({
  hits,
  selectedIndex = 0,
  onActivate,
}) {
  const selectedRef = useRef(null)

  useEffect(() => {
    selectedRef.current?.scrollIntoView?.({
      block: 'nearest',
      inline: 'nearest',
    })
  }, [selectedIndex, hits?.length])

  if (!hits?.length) return null

  return (
    <Box
      component="ul"
      id="search-results"
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
            id={resultOptionId(index)}
            ref={selected ? selectedRef : undefined}
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
            {hit.page != null &&
            String(hit.extension || '').toLowerCase() === 'pdf' ? (
              <Typography
                variant="caption"
                sx={{
                  color: colors.accent,
                  display: 'block',
                  mt: 0.25,
                  fontSize: '0.75rem',
                }}
              >
                Page {hit.page}
              </Typography>
            ) : null}
          </Box>
        )
      })}
    </Box>
  )
}
