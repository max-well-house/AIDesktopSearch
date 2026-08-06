# Guided Ollama setup — Windows install spike (#133a)

Research for in-app guided setup (Wave 3 UI). Goal: get Ollama + default models onto the machine **without** a terminal tutorial as the primary path. Meshen never bundles Ollama into the portable (size / update story).

## Recommended primary path

**Launch the official Windows installer** with normal UAC consent:

| Item | Value |
|------|--------|
| Download | `https://ollama.com/download/OllamaSetup.exe` |
| Landing page | [ollama.com/download/windows](https://ollama.com/download/windows) |
| After install | Ollama usually starts from Start menu / tray; API at `http://127.0.0.1:11434` |

In-app flow (planned for #133b): detect missing/not-running → primary button downloads/opens `OllamaSetup.exe` (or starts an already-downloaded copy) → user completes UAC/installer → Meshen polls `/api/version` → in-app `ollama pull` for models.

## Secondary path: winget

```text
winget install --id Ollama.Ollama -e
```

| Pros | Cons |
|------|------|
| One command, official package id | Still a shell/automation surface; some PCs lack winget or App Installer |
| Good advanced / power-user fallback | May still show UAC; not quieter than the Setup.exe |

Prefer **Setup.exe** as the guided primary action; keep winget as documented advanced fallback (already in [install.md](./install.md)).

## Optional: install.ps1

Ollama documents:

```powershell
irm https://ollama.com/install.ps1 | iex
```

**Do not** use this as Meshen’s primary path — it is still a PowerShell one-liner and feels like a terminal tutorial. Fine as a third-tier advanced note for developers.

## Detection (already in Meshen)

[`backend/capabilities/ollama.py`](../backend/capabilities/ollama.py):

| Status | Meaning |
|--------|---------|
| `available` | `GET /api/version` succeeds |
| `unavailable` | Binary present under LocalAppData/Program Files (or PATH), API down |
| `not_installed` | No binary probe hit and API down |

Guided setup should branch:

1. `not_installed` → offer installer
2. `unavailable` → offer “Start Ollama” / open Start menu hint (or relaunch `ollama.exe` if we can find it)
3. `available` but models missing → in-app pull only

## Models to pull after install

| Model | Role | Issue |
|-------|------|--------|
| `nomic-embed-text` | Semantic embed + query | Already required for v1.0 semantic |
| `llama3.2:3b` | Default chat (#70) | Fits Decision #003 VRAM bar; #99 may allow picking among installed later |

Pull via Ollama HTTP or `ollama pull` spawned with UI progress — never ask the user to paste pull commands as the happy path.

## Failure modes

| Failure | User-visible behavior |
|---------|------------------------|
| User cancels UAC / installer | Classic search works; Semantic/AI stay unavailable with clear copy |
| No admin rights | Installer may fail; show error + link to download page; do not silent-elevate |
| Offline | Cannot download Setup.exe or models; explain network needed once |
| Installer succeeds, service not running | Status `unavailable`; prompt to start Ollama from tray/Start |
| API up, models not pulled | Offer in-app pull with progress/errors |
| Disk full / pull fails | Surface Ollama error text; keep classic usable |

## Out of scope (confirmed)

- Silent install with no consent
- Bundling full Ollama into the portable
- Replacing Ollama with a vendored embed-only runtime (separate research if needed)

## Recommendation for #133b

1. Primary CTA: download/open **OllamaSetup.exe** (OS consent UI).
2. Poll health until `available` or timeout with recovery copy.
3. In-app pull `nomic-embed-text` + `llama3.2:3b` with progress.
4. Success → `semantic_query_ready` / `chat_ready` without a shell.
5. Docs: terminal / winget / install.ps1 = advanced only.
