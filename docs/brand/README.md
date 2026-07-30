# Brand assets

Identity artwork and packaging icons. Product display name is **Meshen** (`app.config.json`); filenames below may still say mosaiq from the earlier working title.

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

**Product identity** lives in root `app.config.json` (not in these image files):

| Field | Controls |
|-------|----------|
| `name` | Display / product name (`Meshen`); portable artifact `Meshen <version>.exe` |
| `company` | Windows CompanyName + copyright |
| `fileDescription` | Windows File description (short). Synced into `package.json` description for the **portable** NSIS wrapper; also applied to unpacked `Meshen.exe` via `afterSign` + rcedit. **Never** rcedit the sealed portable `.exe` (NSIS integrity check fails). |
| `version` | Semver; also shown in Settings — not required in the Explorer description |
| `description` | Longer product pitch in `app.config.json`; not what Explorer shows when `fileDescription` is set |
| `appId` | electron-builder app id (do not change lightly) |

Upload GitHub Release assets as the builder emits them (`Meshen <version>.exe`) — do not rename with a `-windows-portable` suffix.
