import { forwardRef, useEffect } from 'react'
import InputBase from '@mui/material/InputBase'
import Box from '@mui/material/Box'
import SearchIcon from './SearchIcon'
import { colors } from '../../theme'

/**
 * Primary launcher input. Designed for filename, semantic, AI, and commands later.
 * Auto-focuses on mount so the launcher is ready to type immediately.
 */
const SearchBar = forwardRef(function SearchBar(
  { value, onChange, placeholder = 'Search your computer...', autoFocus = true },
  ref,
) {
  useEffect(() => {
    if (!autoFocus) return
    const id = requestAnimationFrame(() => {
      ref?.current?.focus?.()
    })
    return () => cancelAnimationFrame(id)
  }, [autoFocus, ref])

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        px: 2,
        py: 1.5,
        borderRadius: 3,
        bgcolor: colors.surface,
        border: `1px solid ${colors.border}`,
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35)',
        transition: 'border-color 160ms ease, box-shadow 160ms ease',
        '&:focus-within': {
          borderColor: 'rgba(0, 229, 168, 0.45)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(0, 229, 168, 0.22)',
        },
      }}
    >
      <SearchIcon />
      <InputBase
        inputRef={ref}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        fullWidth
        inputProps={{
          'aria-label': 'Search your computer',
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
    </Box>
  )
})

export default SearchBar
