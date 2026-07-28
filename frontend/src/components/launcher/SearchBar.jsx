import { forwardRef, useEffect } from 'react'
import InputBase from '@mui/material/InputBase'
import IconButton from '@mui/material/IconButton'
import Box from '@mui/material/Box'
import SearchIcon from './SearchIcon'
import { colors } from '../../theme'

function ClearIcon() {
  return (
    <Box
      component="svg"
      viewBox="0 0 16 16"
      width={14}
      height={14}
      aria-hidden
      sx={{ display: 'block' }}
    >
      <path
        d="M4.2 4.2a.75.75 0 0 1 1.06 0L8 6.94l2.74-2.74a.75.75 0 1 1 1.06 1.06L9.06 8l2.74 2.74a.75.75 0 1 1-1.06 1.06L8 9.06l-2.74 2.74a.75.75 0 1 1-1.06-1.06L6.94 8 4.2 5.26a.75.75 0 0 1 0-1.06z"
        fill="currentColor"
      />
    </Box>
  )
}

/**
 * Primary launcher input. Designed for filename, semantic, AI, and commands later.
 * Auto-focuses on mount so the launcher is ready to type immediately.
 */
const SearchBar = forwardRef(function SearchBar(
  {
    value,
    onChange,
    onKeyDown,
    onClear,
    placeholder = 'Search your computer...',
    autoFocus = true,
    activeDescendantId,
  },
  ref,
) {
  useEffect(() => {
    if (!autoFocus) return
    const id = requestAnimationFrame(() => {
      ref?.current?.focus?.()
    })
    return () => cancelAnimationFrame(id)
  }, [autoFocus, ref])

  const showClear = Boolean(value?.length)

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        px: 2,
        py: 1.5,
        borderRadius: 3,
        bgcolor: colors.surface,
        border: `1px solid ${colors.border}`,
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35)',
        transition: 'border-color 160ms ease, box-shadow 160ms ease',
        '&:focus-within': {
          borderColor: colors.accentTeal,
          boxShadow: `0 8px 32px rgba(0, 0, 0, 0.45), 0 0 0 1px ${colors.mosaicGlowTeal}`,
        },
      }}
    >
      <SearchIcon />
      <InputBase
        inputRef={ref}
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        fullWidth
        inputProps={{
          'aria-label': 'Search your computer',
          'aria-controls': activeDescendantId ? 'search-results' : undefined,
          'aria-activedescendant': activeDescendantId || undefined,
          spellCheck: false,
          autoComplete: 'off',
          autoCorrect: 'off',
          autoCapitalize: 'off',
        }}
        sx={{
          fontSize: '1.125rem',
          fontWeight: 450,
          color: colors.textPrimary,
          '& input::placeholder': {
            color: colors.textSecondary,
            opacity: 0.85,
          },
        }}
      />
      {showClear ? (
        <IconButton
          aria-label="Clear search"
          size="small"
          onClick={() => {
            onClear?.()
            requestAnimationFrame(() => ref?.current?.focus?.())
          }}
          sx={{
            color: colors.textSecondary,
            p: 0.5,
            flexShrink: 0,
            '&:hover': {
              color: colors.textPrimary,
              bgcolor: colors.hover,
            },
          }}
        >
          <ClearIcon />
        </IconButton>
      ) : null}
    </Box>
  )
})

export default SearchBar
