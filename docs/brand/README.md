# Brand assets

Identity artwork and packaging icons.

| Asset | Purpose |
|-------|---------|
| `mosaiq-identity-guide.png` | Full identity sheet (palette, mark, principles) |
| `mosaiq-mark.png` | Original light-plate mark (reference) |
| `app-mark-dark.png` | **Source** app icon (dark `#0D1117` plate) |

**Runtime icons** (generated — do not hand-edit):

| Asset | Purpose |
|-------|---------|
| `resources/icon.ico` | Windows exe / shortcut icon (dark `#0D1117` plate) |
| `resources/icon.png` | 256px packaging icon |
| `frontend/public/app-mark.png` | In-app / favicon mark on dark plate |
| `frontend/public/favicon.svg` | Vector favicon with dark plate |

Regenerate after changing the source mark:

```bash
npm run icons
```

**Product name / company / version** live in root `app.config.json` — not in these files.
