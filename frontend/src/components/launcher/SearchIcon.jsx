import { colors } from '../../theme'

/** Minimal search glyph — avoids pulling in an icon package for one mark. */
export default function SearchIcon({ size = 22 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      style={{ flexShrink: 0, opacity: 0.7 }}
    >
      <circle cx="11" cy="11" r="6.5" stroke={colors.accent} strokeWidth="1.75" />
      <path
        d="M16.2 16.2L20 20"
        stroke={colors.accent}
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  )
}
