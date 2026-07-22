import appConfig from '@app-config'

/**
 * App brand mark — mosaic M with semantic network.
 * Display name comes from app.config.json so renames stay centralized.
 */
export default function AppMark({ size = 28, title = appConfig.name }) {
  return (
    <img
      src={`${import.meta.env.BASE_URL}app-mark.png`}
      width={size}
      height={size}
      alt={title}
      draggable={false}
      style={{
        display: 'block',
        objectFit: 'contain',
        userSelect: 'none',
      }}
    />
  )
}
