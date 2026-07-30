/**
 * Convert a KeyboardEvent into an Electron accelerator string (#138).
 * Returns null while only modifiers are held.
 */
export function eventToAccelerator(event) {
  const mods = []
  // Windows-first: prefer Control over Meta/Win for globalShortcut.
  if (event.ctrlKey) mods.push('Control')
  else if (event.metaKey) mods.push('Super')
  if (event.altKey) mods.push('Alt')
  if (event.shiftKey) mods.push('Shift')

  const key = event.key
  if (
    key === 'Control' ||
    key === 'Alt' ||
    key === 'Shift' ||
    key === 'Meta' ||
    key === 'OS'
  ) {
    return null
  }

  let keyName
  if (key === ' ') keyName = 'Space'
  else if (key === '+') keyName = 'Plus'
  else if (key === '-') keyName = '-'
  else if (key.length === 1) keyName = key.toUpperCase()
  else keyName = key

  // Global shortcuts without a modifier steal typing focus — require one.
  if (mods.length === 0) return null

  return [...mods, keyName].join('+')
}

export const DEFAULT_LAUNCHER_SHORTCUT_LABEL = 'Alt+Space'
