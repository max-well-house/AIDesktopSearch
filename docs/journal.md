# Notes

Scratchpad for decisions, open questions, and research. Prefer short dated entries.

## 2026-07-14
Goal:
Setup project folders, github repo, and project board

What I learned:
how much goes into planning and prepping

Problem:
i mnot usually great at this

Solution:
use the help of agents to help me understand what to do, where to do it, and why to do it

Next:
Launch the app (Milestone v0.1)

## 2026-07-14 â€” Stack lock

Locked Electron + React + Python/FastAPI (Decision #001).
Locked hybrid search (Decision #002) and operability bar for this PC first (Decision #003: i5-14400F, 16GB DDR5, RTX 5060 Ti 8GB).
Next: Architecture Spike (v0.0.2) then Desktop Shell (v0.1).

## 2026-07-14 â€” Architecture spike (Electron â†” FastAPI)

Goal:
Prove the desktop shell can call the local FastAPI hello endpoint and show the result.

What I did:
- `npm init` + Electron (`frontend/main.js` entry, `npm start`)
- Kept FastAPI hello in `backend/main.py`
- Wired main â†’ preload â†’ renderer so the UI shows hello JSON or a connection error

What I learned:
Loading `backend/main.py` via `loadFile` does not call the API â€” it just opens the source file. The API must be requested over HTTP at `http://127.0.0.1:8000/`. Calling from the Electron main process (`net.fetch`) keeps CORS out of the way for this spike.

Problem:
Early scaffold mixed "show a page" with "talk to the backend."

Solution:
`index.html` + `renderer.js` for UI; `preload.js` bridge; `main.js` owns the FastAPI request and surfaces errors.

Next:
Finish v0.0.2 leftovers (React + MUI in the renderer; Ollama optional), then Desktop Shell (v0.1).

## 2026-07-14 â€” React â†” Electron â†” FastAPI pipeline

Goal:
Prove the lasting endpoint framework with a Backend Connection Test UI.

What I did:
- Split `electron/` (main + preload) from `frontend/` (Vite + React)
- Enriched FastAPI `GET /` with status / version / timestamp / message
- Wired React â†’ `window.api.checkBackend` â†’ Electron `net.fetch` â†’ FastAPI â†’ UI
- `npm run dev` runs Vite + Electron together

What I learned:
The spike is not "can React call HTTP?" â€” it is proving React never talks to FastAPI directly so later endpoints reuse the same Electron gatekeeper.

Next:
v0.0.3 System Capability Detection, then Desktop Shell (v0.1).

## 2026-07-14 â€” System Capability Detection (v0.0.3)

Goal:
Report what the machine can do without crashing when Ollama is missing.

What I did:
- `GET /health` with extensible `capabilities` (ollama probe, gpu/models stubs)
- Electron IPC â†’ `/health`; React System Status UI
- Capability Principle in vision; Decision #003 capability-based GPU rule

Next:
Manual verification matrix, then Desktop Shell (v0.1) + Material UI.

## 2026-07-15 â€” Desktop Shell (v0.1.0)

Goal:
Land a real desktop shell: React + MUI window, hot reload, packaged build, docs in sync.

What I did:
- Material UI System Status screen; `npm run dev` Vite + Electron hot reload
- electron-builder packaging (`npm run package` / `package:portable` â†’ `release/`)
- Updated `docs/architecture.md` (and README / tech-stack / roadmap) to match the process model

What I learned:
Packaging the shell is separate from shipping Python. Freezing FastAPI into the `.exe` is heavier than spawning the repo `.venv` later (#96).

Next:
#96 â€” Electron starts/stops FastAPI for one-command testing; then v0.2.0 Search Launcher (shortcut, tray, Escape).

## 2026-07-15 â€” Board audit (pre-forward)

Goal:
Clean milestones/issues after Desktop Shell so the next work is obvious.

What I did:
- Closed finished milestones v0.0.1 and v0.0.2; created **v0.1.1 Backend Lifecycle** for #96
- Closed #97 as duplicate of #40; cross-linked #98â†”#69, #65â†”#95/#70, shortcut note on #30
- Added gap issues #111 (ship Python with package) and #112 (GPU detection beyond stub)
- Wrote `docs/audit-2026-07-15.md`; synced roadmap, ideas, learning notes

## 2026-07-22 â€” Backend lifecycle (#96)

Goal:
One-command testing: Electron attaches to or spawns FastAPI; stops only what it owns.

What I did:
- Added `electron/backendProcess.js` (probe â†’ attach / spawn from `.venv` / tree-kill stop)
- Wired `ensureBackend` before `createWindow` and `stopBackend` on `before-quit`
- Updated README + architecture process model for one-command / attach workflow

What I learned:
Owned children should not use uvicorn `--reload` on Windows â€” the reloader process tree is easy to orphan. Attach mode keeps a manual `--reload` terminal safe.

Next:
Close v0.1.1 on the board when verified; start v0.2.0 Search Launcher (shortcut, tray, Escape).

## 2026-07-22 — Launcher foundation (#31) + brand

Goal:
Ship the permanent search-launcher UI foundation and a rename-ready product identity.

What I did:
- Built launcher shell: SearchBar, MosaicCanvas (idle), EmptyState, Footer; mosaic fades when typing
- Brand palette + mosaic-M mark; dark `#0D1117` desktop `.ico`; `app.config.json` as single source for name/company/version
- Closed #31 search input (auto-focus included in SearchBar)

What I learned:
Windows shortcuts need a real multi-size `.ico` with a dark plate — light/white icon plates look cheap on the desktop. Product display names should not be hardcoded once packaging and UI both need them.

Next:
#32 autofocus issue (likely already satisfied — verify/close), #33 Escape, #34 tray; then real search wiring.

## 2026-07-23 â€” Search Launcher milestone (v0.2.0)

Goal:
Finish Phase 2 Search Launcher: shortcut, dismiss/toggle, tray, startup, polish â€” close the milestone.

What I did:
- Closed #32 (autofocus already in SearchBar from #31)
- #33 Escape dismiss (clear + hide) + Alt+Space toggle (keep query); scrub-on-reopen so no stale-text flash
- #34 System tray (Show / Quit; X hides; tray click toggles by visibility)
- #35 Start with Windows tray checkbox (`setLoginItemSettings`; unpackaged shows as Electron in Startup)
- #36 Window size session-only (keep while hidden; Quit â†’ default 720Ã—480)
- #37 Launcher screenshots in README + `docs/screenshots/`
- Closed GitHub milestone **v0.2.0 - Search Launcher** (8/8 issues)

What I learned:
- Tray click steals focus before the handler runs â€” toggle must use visibility, not `isFocused()`
- Windows `getLoginItemSettings` needs the same `path`/`args` as set, or the menu checkmark lies
- Packaged desktop shortcuts go stale; rebuild after shell UX lands or Esc/Alt+Space look "broken"

Next:
v0.3.0 File Indexer â€” opt-in folders (#40), SQLite filename search, hybrid routing stub (#98). Rebuild portable exe when daily-driving the shortcut.

## 2026-07-23 â€” Filesystem watcher research (#38)

Goal:
Decide how Phase 4 should detect file changes without implementing watching yet.

What I did:
- Compared watchdog, Chokidar, fs.watch, polling, and raw OS APIs
- Chose Python `watchdog` in FastAPI (Decision #005); Chokidar as alternate; polling as startup/fallback
- Documented event pipeline (queue â†’ debounce â†’ batch â†’ SQLite) and Phase 4 requirements in `docs/research-filesystem-watchers.md`
- Closed #38

What I learned:
Mac/Linux later does not favor Chokidar â€” both libraries wrap the same native APIs. Architecture ownership (brain vs shell) matters more than the npm-vs-pip brand.

Next:
v0.3.0 implementation â€” SQLite (#39), scan folders (#40), filename index/search; leave live watching for v0.4.

## 2026-07-23 ? End of day (v0.3 kickoff)

Goal:
Start File Indexer after closing Search Launcher; lock watcher research; get metadata into SQLite with a visible confidence cue.

What I did:
- Closed **v0.2.0 Search Launcher** earlier today (#30?#37)
- #38 Watcher research ? Decision #005 (`watchdog` in FastAPI); docs in `research-filesystem-watchers.md`
- #39 SQLite init on API startup (`data/index.db`, `roots` + `files`)
- #113 Test corpus generator (fixtures outside the repo)
- #41 Save metadata ? scan upsert/replace, Footer **Indexed: N files**, System Status Browse/Scan (user-verified)

What I learned:
- Milestone framing matters: watcher research lives in v0.3 but product goal is still filename search; live watching is v0.4
- A durable Footer stub (`Indexed`) beats a throwaway debug screen for ?did the step work??

Next:
1. #40 ? proper opt-in folder add/remove UX (scan API already exists)
2. #42 ? filename search against SQLite
3. #47 ? document schema; tighten #45/#46 ignores as needed

## 2026-07-23 â€” End of day (v0.3 kickoff)

Goal:
Start File Indexer after closing Search Launcher; lock watcher research; get metadata into SQLite with a visible confidence cue.

What I did:
- Closed **v0.2.0 Search Launcher** earlier today (#30â€“#37)
- #38 Watcher research â†’ Decision #005 (`watchdog` in FastAPI); docs in `research-filesystem-watchers.md`
- #39 SQLite init on API startup (`data/index.db`, `roots` + `files`)
- #113 Test corpus generator (fixtures outside the repo)
- #41 Save metadata â€” scan upsert/replace, Footer **Indexed: N files**, System Status Browse/Scan (user-verified)

What I learned:
- Milestone framing matters: watcher research lives in v0.3 but product goal is still filename search; live watching is v0.4
- A durable Footer stub (`Indexed`) beats a throwaway debug screen for "did the step work?"

Next:
1. #40 â€” proper opt-in folder add/remove UX (scan API already exists)
2. #42 â€” filename search against SQLite
3. #47 â€” document schema; tighten #45/#46 ignores as needed

## 2026-07-24 — End of day (v0.3 File Indexer complete)

Goal:
Finish v0.3: classic filename search end-to-end, ignore rules, routing stub, schema docs, footer freshness.

What I did:
- #40 opt-in corpus roots; #42–#44 search / results / open file
- #45/#46 shared scan ignore (`ignore.py`)
- #98 classic-first routing stub (`backend/search/routing.py`); no embeddings
- #115 Footer Indexed date from `last_indexed_at`
- #47 `docs/schema.md`; closed milestone **v0.3.0 - File Indexer**
- Logged zero-hit suggestions / fuzzy as post-v1 idea in `docs/ideas.md`

What I learned:
- Routing stub is not hybrid ranking; keep #69 for embeddings
- Footer date is enough freshness cue until live watching (v0.4)

Next:
1. Start **v0.4.0 Live File Watching** — Decision #005 / #48–#51 (`watchdog` in FastAPI)
2. Reuse `indexer/ignore.py` in the watcher path
3. Keep classic search working without Ollama while watching lands

## 2026-07-24 — History scrub + privacy rule

Goal:
Remove personal home path from git history; prevent repeat leaks.

What I did:
- git filter-repo replaced absolute home clone paths (e.g. `C:\Users\<you>\...`) across history; force-pushed main
- Added always-on Cursor rule no-personal-paths.mdc; track .cursor/rules/ in git
- README already used portable repo-root wording on tip

What I learned:
- A single absolute cd in the README lives in every later blob until history is rewritten
- filter-repo finishes in seconds on a small repo; force-push is the real product cost (stale SHAs)

Next:
1. Start v0.4 live watching when ready

## 2026-07-24 — PDF library research (#53)

Goal:
Compare PDF libraries for Phase 5; lock a recommendation before extract/FTS code.

What I did:
- Wrote `docs/research-pdf-libraries.md` (speed, accuracy, per-page, license, packaging)
- Accepted Decision #006 — PyMuPDF in FastAPI; thin per-page contract; OCR/embeddings deferred
- Synced roadmap, tech-stack, architecture, schema note, learning-notes

What I learned:
- Phase 5 should not design the forever multi-format ingestion platform; thin extract unblocks #54–#57
- AGPL is a packaging-visible tradeoff; pypdf stays the documented alternate

Next:
1. #54 Read PDF text (`pymupdf` + soft-fail)
2. #55 Save text / FTS schema
3. #56–#57 Search inside PDFs + page hints

## 2026-07-24 — PDF content search (#54–#57)

Goal:
Ship Phase 5 vertical slice: extract → store → search → page caption.

What I did:
- Schema v2: `file_content` + `file_pages_fts` + delete trigger
- `pymupdf` extract with soft-fail / size+page caps; sync on scan/watch upsert/rename
- Classic search merges filename LIKE + FTS; one hit per file with `page` / `match`
- Launcher `ResultsList` shows Page N; open still `shell.openPath`

What I learned:
- Per-page FTS from day one avoids a redesign for #57
- True open-to-page is viewer-specific on Windows — surface page instead

Next:
1. #58 Faster parsing (or defer) then close v0.5.0 milestone
2. Start v0.6 document types when ready

## 2026-07-25 — End of day (v0.5 complete + board hygiene)

Goal:
Finish Phase 5 PDF performance (#58), close v0.5.0, and shape new pre-v1.0 polish issues so the board matches the rest of the project.

What I did:
- Shipped #58 — batched FTS writes, extract time budget, yield between PDFs, scan off the event loop; closed v0.5.0 milestone
- Formatted #118 (per-root auto-watch), #120 (footer capability lights), #121 (hide native menu / theme chrome & scrollbars) with acceptance criteria → **v1.0.0 Daily Driver**
- Formatted #116 / #117 / #119 as post–v1.0 nice-to-haves (no milestone)
- Synced `docs/roadmap.md` v1.0.0 bullets for #118 / #120 / #121

What I learned:
- Don’t invent a “0.9 polish” milestone when **v0.9.0 is already Images** — corpus/footer/chrome polish belongs in Daily Driver alongside Settings / #86
- New issues stay useful when they get the same Phase / Goal / AC / Out of scope shape as #114

Next:
1. Start **v0.6.0 Documents** (DOCX / TXT / Markdown)
2. Keep #118 / #120 / #121 queued for v1.0; don’t block v0.6 on them

## 2026-07-27 — Phase 6 Documents (v0.6.0)

Goal:
Ship unified document parsers so classic FTS covers DOCX / TXT / Markdown alongside PDF.

What I did:
- #62 — `ExtractResult` + `CONTENT_EXTENSIONS` registry; migrate PDF; leftover content clear; Page N UI gated to PDF (Decision #007)
- #60 — stdlib TXT extract with encoding fallbacks
- #61 — Markdown `.md` / `.markdown` indexed raw (headings preserved for search)
- #59 — `python-docx` paragraphs + tables; soft-fail corrupt files
- Manual checks: body tokens in nested TXT, Phoenix README.md, Charizard.docx/pdf

What I learned:
- Content FTS is whole-token today (filename stays substring) — typeahead body prefix is later polish
- Corpus generator stubs are not real Office/PDF binaries; hand-edited real files are better for content tests

Next:
1. Start **v0.7.0 Semantic Search** when ready
2. Optional: extend `tools/corpus/generate.py` with real TXT/MD/DOCX bodies
3. Keep #118 / #120 / #121 queued for v1.0

## 2026-07-27 — Phase 7 kickoff (v0.7.0 Semantic Search)

Goal:
Execute semantic search in dependency order so classic search stays AI-independent.

What I did:
- Locked Phase 7 plan: store foundation (#67) → generate (#66) → semantic endpoint (#68) → hybrid (#69); #112 GPU in parallel
- Defaults: `nomic-embed-text` via Ollama; sqlite-vec in same `index.db`; page-aware PDF chunks; classic-first hybrid escalate
- Research gate already closed (#63–#65); implementation starts with #67

What I learned:
- Pipeline narrative is “chunk → embed → store,” but code needs the store/schema first so generate has a write target
- Generate ≠ query: building vectors needs Ollama; searching stored vectors must still work when Ollama is down (Decision #003 / #008)

Next:
1. Ship **#67 Store embeddings** (sqlite-vec load, schema, soft-fail, System Status visibility)
2. Then #66 → #68 → #69 one issue at a time with manual UI checks between commits

## 2026-07-27 — Phase 7 pause after #66

Goal:
Land store + generate for semantic search, then pause before the query/hybrid path.

What I did:
- #67 — sqlite-vec in `index.db`, soft-fail, System Status verify smoke (closed earlier)
- #66 — chunker, Ollama `nomic-embed-text` client, pauseable embed queue, content-sync enqueue, backfill API; manual corpus embed (~28 chunks)
- #122 opened — Diagnostics UX wrap (no instructional walls; contextual actions); interim UI: live refresh while queue drains, hide Embed/Pause when idle, Embedded sample list
- Paused Phase 7 plan before #68 / #69 / #112

What I learned:
- Diagnostics lab buttons need status-driven visibility, not essay copy (#122)
- Generate ≠ query still holds: vectors in DB do not turn on footer Semantic until #68

Next (pick up here):
1. **#68** Semantic search endpoint — query embed + k-NN + `run_semantic` / launcher path
2. **#69** Hybrid search (Decision #002)
3. **#112** GPU detection (parallel); **#122** Diagnostics UX after core path

## 2026-07-27 — #68 Semantic search (in progress)

Goal:
Query by meaning using stored vectors + query embed; thin launcher wire before full hybrid (#69).

What I did:
- `run_semantic` — Ollama embed query → knn → file hits (`match: semantic`)
- `GET /search?mode=classic|semantic|auto` (auto = classic then empty→semantic)
- Launcher uses `auto`; footer Semantic **Available** when chunk count > 0
- Manual: `fire dragon pokemon` → Charizard.pdf (Page 4) via semantic salvage

Next:
1. **#69** Hybrid search (Decision #002)
2. **#112** GPU detection (parallel); **#122** Diagnostics UX after core path

## 2026-07-27 — #69 Hybrid search (in progress)

Goal:
Merge classic + semantic so meaning queries get both keyword hits and vector fills; filename-like stays classic-only.

What I did:
- `classify_query` / `is_filename_like` — short names and `*.ext` stay classic
- `merge_hybrid_results` — classic order wins; semantic fills; overlap → `match: hybrid`
- `mode=auto|hybrid` uses merge when vectors ready; soft-falls to classic if Ollama down (LLM still off)
- Manual: `fire dragon p` → Charizard.pdf/docx + other meaning hits; footer Semantic Available

Next:
1. **#112** GPU detection and/or **#122** Diagnostics UX
2. Milestone v0.7.0 close when #112/#122 resolved or deferred

## 2026-07-28 — Embed / semantic audit

Goal:
Confirm nomic-embed-text + sqlite-vec + semantic/hybrid search are set up correctly (pass/fail gates; no routing fixes).

What I did:
- Gate A: 26 pytest passed (store, generate, semantic, routing, ollama)
- Gate B: live `/health` + smoke OK (28 chunks, dim 768, model present, GPU detected)
- Gate C: search matrix — pipeline hard gates green; C4/C8 document ≤2-token auto skip
- Gate D: doc vs code — query still needs live Ollama embed (research note outdated)
- Wrote `docs/audit-embed-semantic-2026-07-28.md`

What I learned:
Pipeline is fine; “pokemon” / “fire dragon” pain is auto routing (classic-only for short queries), not a bad embed model. Forced `mode=semantic` already links `pokemon` → Charizard.docx (piplup) at rank #2.

Next:
1. Routing follow-ups from audit (empty-classic escalate; short-concept hybrid; optional distance floor)
2. Align “Semantic Available” / docs with real query requirements

## 2026-07-28 — Audit follow-ups shipped

Goal:
Make auto search match “barely remember” queries without always burning embeds on exact filenames.

What I did:
- `is_filename_like` only for empty / `*.ext`; short concepts → hybrid
- Empty classic escalates to semantic when vectors ready
- `SEMANTIC_MAX_DISTANCE = 0.52` (keep nearest always)
- `/index/status.semantic_query_ready` + launcher footer; docs corrected for live query embed

Next:
1. Manual smoke: `pokemon`, `fire dragon`, `Charizard.pdf` in the launcher
2. **#122** Diagnostics UX / v0.7 close

## 2026-07-28 — #122 Diagnostics UX / v0.7 wrap

Goal:
Daily-user Diagnostics: Status vs Advanced, opt-in Start embedding + done confirmation, then close v0.7.0.

What I did:
- Content sync no longer auto-enqueues embeddings; pending stays discoverable until **Start embedding** (backfill)
- System Status: Check / Start / Pause·Resume primary; **Verify vector store** under Advanced; live queue shows done/failed; run done confirmation
- Docs/README: generate vs query once; roadmap/architecture/tech-stack/research open-Qs cleaned
- Routing smoke (API / unit): short-concept hybrid + filename classic covered by `tests/test_query_routing.py`; launcher checklist still worth a quick eye-pass

What I learned:
- Lab buttons need grouping + contextual visibility, not essay copy
- Done confirmation needs a wasActive/fast-finish race guard so empty-queue snapshots do not false-confirm

Next:
1. Close #122 + milestone v0.7.0 on the board
2. v0.8 RAG / LLM (#70) when ready; offline query-embed + score fusion stay deferred

## 2026-07-28 — Board slim for v1.0 foundation

Goal:
Storeable classic+semantic search as v1.0; RAG/Images after; cool features → nice to have.

What I did:
- Opened **#124** Product slim (auto-embed, Pause stays, lab under Details)
- Expanded #80 Settings, concrete #86 Polish, narrowed #120 / #85 / #83 / #111
- Demoted #81/#82/#84/#87 to nice to have (after v1.0 + v2.x)
- Retitled milestones: v0.7 closed; **v2.0 Local AI** (was 0.8); **v2.1 Images** (was 0.9); v1.0 = search Daily Driver
- Roadmap / ideas updated to match

What I learned:
- v1.0 was overweight; fewer features done well beats Favorites/History on day one
- Opt-in Start embedding fought the product promise — auto-embed + Pause is the daily path

Next:
1. Implement **#124** product slim (code)
2. #80 Settings rehome → #121 chrome → #120 footer → packaging #111

## 2026-07-28 — Semver: 1.1 / 1.2 not 2.0 for RAG/Images

Goal:
Same product grows as 1.x; save v2.0 for a later era.

What I did:
- Retitled milestones to **v1.1.0 Local AI** and **v1.2.0 Images**; v1.0 description notes true v2.0 is TBD
- Opened **#125** — show version in Settings (not launcher watermark)
- Added Cursor rule `challenge-suggestions.mdc` — push back on weak or flip-flop suggestions
- Roadmap synced

What I learned:
- Version in-app is useful for support; floating corner chrome is clutter
- Max asked to be challenged when suggestions are bad or half-baked

Next:
1. **#124** product slim code
2. #80 / #125 version line when Settings lands

## 2026-07-29 — Post-1.0 backlog → eras

Goal:
Turn the dump milestone into real issues and a long-term era/milestone roadmap.

What I did:
- Triaged **To be planned** — fleshed, merged, or closed (voice/email/calendar/browser/plugins host/favorites/etc.)
- Eras on the board: **1.x Find** (Up next, 1.1–1.3) → **2.x Act** (2.1–2.2) → **3.x Expand** (3.1–3.2 research-gated) → **4.x Connect** (4.1 sync)
- Renamed dump → **Unplanned** (empty open); added #133–#139 (Ollama setup, AV research, packaging identity, updates, shortcut, excludes)
- Cursor rule: **close-out-milestone** → release notes + GitHub Release when a milestone ships
- `docs/roadmap.md` / `docs/ideas.md` synced

What I learned:
- Milestone = shippable version; era = product chapter; 2.0 starts Era 2, not “1.x backlog empty”
- “Plugin” meant parsers/previews/capabilities — not a third-party host

Next:
1. **Up next** polish (#136 exe identity first is fine)
2. Then **v1.1** Local AI must-ship (#70–#72, #133, #75, **#140** corpus eval)

## 2026-07-29 — Corpus companions + expected hits

Goal:
Keep regenerable test corpus outside the repo; each milestone that needs new fixture kinds gets a Corpus issue with query → must_include paths (fail otherwise).

What I did:
- Opened #140–#144 (1.1 / 1.2 / 1.3 / 2.1 / 3.1); #140 is 1.1 must-ship
- Updated `tools/corpus/README.md` + roadmap corpus policy

Next:
Implement #140 when starting Local AI / deeper search work — not before Up next if polishing first.

