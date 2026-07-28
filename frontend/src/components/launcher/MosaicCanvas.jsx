import { useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import { colors } from '../../theme'

const CELL = 7
const GAP = 3
const STRIDE = CELL + GAP

const GLOW_BASE = [
  colors.mosaicGlowTeal,
  colors.mosaicGlowCyan,
  colors.mosaicGlowBlue,
]

/** Replace the alpha channel in an rgba(...) token. */
function withAlpha(rgba, alpha) {
  return String(rgba).replace(/[\d.]+\s*\)$/, `${alpha})`)
}

/**
 * Idle-state brand surface: a dormant grid of file-tiles.
 * Stays mounted permanently; parent controls visibility/opacity.
 * RAF pauses when inactive or when the document is hidden (#85).
 */
export default function MosaicCanvas({ active = true }) {
  const canvasRef = useRef(null)
  const rafRef = useRef(0)
  const [pageVisible, setPageVisible] = useState(
    () => typeof document === 'undefined' || document.visibilityState !== 'hidden',
  )

  useEffect(() => {
    const onVisibility = () => {
      setPageVisible(document.visibilityState !== 'hidden')
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  const animate = active && pageVisible

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return undefined

    const ctx = canvas.getContext('2d')
    let width = 0
    let height = 0
    let cols = 0
    let rows = 0
    /** Sparse glow cells: { c, r, phase, hue } */
    let glows = []

    function resize() {
      const parent = canvas.parentElement
      if (!parent) return
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = parent.clientWidth
      height = parent.clientHeight
      canvas.width = Math.max(1, Math.floor(width * dpr))
      canvas.height = Math.max(1, Math.floor(height * dpr))
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      cols = Math.ceil(width / STRIDE) + 1
      rows = Math.ceil(height / STRIDE) + 1
      const count = Math.max(8, Math.floor((cols * rows) / 90))
      glows = Array.from({ length: count }, () => ({
        c: Math.floor(Math.random() * cols),
        r: Math.floor(Math.random() * rows),
        phase: Math.random() * Math.PI * 2,
        hue: Math.floor(Math.random() * 3),
      }))
    }

    function draw(time) {
      ctx.clearRect(0, 0, width, height)

      const t = time * 0.001
      ctx.fillStyle = colors.mosaicDim
      for (let r = 0; r < rows; r += 1) {
        for (let c = 0; c < cols; c += 1) {
          const x = c * STRIDE
          const y = r * STRIDE
          ctx.fillRect(x, y, CELL, CELL)
        }
      }

      for (const glow of glows) {
        const pulse = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 0.7 + glow.phase))
        const alpha = 0.07 + pulse * 0.14
        const base = GLOW_BASE[glow.hue % GLOW_BASE.length]
        const scale = glow.hue === 1 ? 0.9 : glow.hue === 2 ? 0.85 : 1
        ctx.fillStyle = withAlpha(base, alpha * scale)
        ctx.fillRect(glow.c * STRIDE, glow.r * STRIDE, CELL, CELL)
      }

      // Occasionally migrate a glow so the grid feels alive without noise
      if (Math.random() < 0.02 && glows.length) {
        const i = Math.floor(Math.random() * glows.length)
        glows[i] = {
          c: Math.floor(Math.random() * cols),
          r: Math.floor(Math.random() * rows),
          phase: Math.random() * Math.PI * 2,
          hue: Math.floor(Math.random() * 3),
        }
      }

      if (animate) {
        rafRef.current = requestAnimationFrame(draw)
      }
    }

    const ro = new ResizeObserver(() => resize())
    if (canvas.parentElement) ro.observe(canvas.parentElement)
    resize()

    if (animate) {
      rafRef.current = requestAnimationFrame(draw)
    } else {
      // One static frame while faded out / inactive / hidden
      draw(0)
    }

    return () => {
      ro.disconnect()
      cancelAnimationFrame(rafRef.current)
    }
  }, [animate])

  return (
    <Box
      aria-hidden="true"
      sx={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
      }}
    >
      <canvas ref={canvasRef} />
    </Box>
  )
}
