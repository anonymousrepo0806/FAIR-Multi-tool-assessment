# FAIR Multi-Assessor

A web application that assesses a research resource with three independent
FAIR tools — **F-UJI**, **FAIR-Checker**, **KGHeartBeat** — normalises their
output onto a shared mapping, computes a cross-tool consensus, and generates
an OpenAI-based plain-language explanation.

## Run it (Docker — the standalone way)

This is one app, three containers, one command:

```bash
cp .env.example .env   # fill in OPENAI_API_KEY if you want AI explanations
docker compose up --build
```

Then open **http://localhost** — that's it. The app opens on **LOD Cloud**
(browse the precomputed, already-agreed-upon assessment across 2,784 KGs
spanning all 11 LOD sub-cloud categories — BLOD, che-cloud, and nine
others — plus, within BLOD, its individual source repositories (Bio2RDF,
BioPortal, GitHub, Wikidata, and more), all through one combined dropdown,
instantly, no waiting on live tools), with a **New Assessment** tab
alongside it for running the three tools live against a URL or uploaded
file. `docker compose` starts:

| Container | What it is | Reachable at |
|---|---|---|
| `fuji` | F-UJI's own official prebuilt image (`ghcr.io/pangaea-data-publisher/fuji`) | `:1071` (internal + exposed for debugging) |
| `backend` | This project's FastAPI app | `:8000` (internal + exposed for debugging) |
| `frontend` | The React app, built and served by nginx, which also **proxies** `/assess`, `/explain`, `/health`, `/docs` to the backend container | **`:80` — the single entry point** |

You never need to configure a frontend/backend URL yourself: nginx proxies
API calls to `backend:8000` over Docker's internal network, and the backend
reaches F-UJI at `fuji:1071` the same way — both by Docker service name, set
automatically in `docker-compose.yml`.

To stop everything: `docker compose down`. To rebuild after changing code:
`docker compose up --build` again.

**A note on FAIR-Checker and KGHeartBeat**: FAIR-Checker needs no container —
it's a public API the backend calls directly. KGHeartBeat has no live public
API to containerise (see "Tool availability" below); it runs in Docker with
everything else but will report "not assessed" for any resource unless you
configure `KGHEARTBEAT_API_URL` in `.env`.

**Honesty note on this delivery**: the compose file, both Dockerfiles, and
the nginx config were built and statically verified (valid YAML, matching
service names/ports between files, correct nginx brace/statement structure)
in an environment without Docker installed, so `docker compose up` itself
was not run end-to-end before delivery. The backend and its mapping logic
*were* verified with real HTTP requests (see below); the Docker wiring
specifically should work by construction but treat your first `docker
compose up --build` as the real first test of it.

## Run it without Docker (manual, two terminals)

```
fair-multi-assessor/
├── backend/     FastAPI — /assess, /assess/batch, /explain
└── frontend/    React + Vite — Dashboard with three view modes + AI panel
```

## Before you run anything: tool availability is not equal

This is the single most important thing to know before deploying this.

| Tool | Availability |
|---|---|
| **FAIR-Checker** | Public API, no setup. Works immediately. |
| **F-UJI** | **No public API.** Requires a running F-UJI server (`fuji_server`), configured via `FUJI_API_URL` / `FUJI_USER` / `FUJI_PASSWORD`. If unreachable, the assessment for F-UJI fails cleanly with a visible error in the UI — the other tools still run and the app does not crash (graceful degradation, as specced). |
| **KGHeartBeat** | **No live public API.** This tool supports a self-hosted live endpoint via `KGHEARTBEAT_API_URL` if you have one; without it, KGHeartBeat is reported as "not assessed" with an explicit reason, never silently scored as zero. |

### Backend setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY, FUJI_API_URL, etc.
uvicorn main:app --reload --port 8000
```

Verify it's running:
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Tested endpoints (verified working in this build)

- `GET  /health` — returns `{"status": "ok"}`
- `POST /assess` — single URL or first row of an uploaded CSV/JSON; runs the
  three tools concurrently via `asyncio.gather`, confirmed ~3x faster than
  sequential (three simulated 1s calls complete in ~1s, not ~3s)
- `POST /assess/batch` — every row of an uploaded CSV/JSON (not in the
  original single-target API contract, but added — a real upload will
  usually have more than one row, and silently dropping the rest would be
  worse than an explicit batch endpoint)
- `POST /explain` — OpenAI explanation; degrades gracefully with a clear
  markdown message if no API key / package is configured, rather than
  erroring the whole request

All four were tested with real HTTP requests during development (see the
build session for the raw request/response pairs), not just unit-tested in
isolation.

### Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local   # set VITE_API_BASE_URL if not localhost:8000
npm run dev
```

**Note on this delivery**: `npm install` was NOT run to completion in the
environment this was built in — that sandbox's filesystem doesn't support
symlinks, which `npm install` requires, and is unrelated to the code itself.
Run `npm install` on your own machine; the `package.json` dependency
versions are pinned to versions known to be mutually compatible
(React 18.3, recharts 2.12, axios 1.7, react-markdown 9).

### What's implemented and working by construction

- **Input handling**: URL or file upload, with client-side validation
  (URL shape, file extension) before submission — `InputPanel.jsx`
- **Three view modes**: Mapped (`ToolScoreView.jsx`, radar chart + table),
  Native (`NativeScoreView.jsx`, each tool's own score, explicitly labelled
  as not cross-comparable), Consensus (`ConsensusView.jsx`, bar chart +
  per-dimension agreement badges)
- **AI Explanation panel**: collapsible, with a Regenerate button
  (`AIExplanation.jsx`), rendering the backend's fixed-section markdown via
  `react-markdown`
- **Export**: JSON download works fully client-side. **PDF export uses the
  browser's native print dialog** (`window.print()` with print-specific
  CSS hiding input controls) rather than a dedicated PDF library — this is
  a deliberate simplification: it requires no extra dependency or
  server-side rendering, but the user gets "Print to PDF" via their
  browser rather than a one-click styled PDF file. Swap in `jspdf` +
  `html2canvas` if a literal one-click PDF download is required.
- **Loading state**: shows which tools are running while the request is in
  flight

### Known gaps against the full spec (not built, by scope)

- **History storage** (SQLite/Postgres) — listed as optional in the spec;
  not implemented. Every assessment is stateless per-request.
- **Caching** of URL assessments (1hr TTL) — not implemented. Every
  request re-runs all tools live. Would be a small addition
  (`functools.lru_cache` with a TTL wrapper, or Redis, in `routers/assess.py`)
  if needed.
- **Reachability pre-check** on URL input — the frontend validates URL
  *shape* only; it does not HEAD-check reachability before submitting,
  since that check would itself need a backend round-trip and the
  three-tool assessment already surfaces unreachable-resource errors
  per-tool.

## Four pages

- **LOD Cloud** (`GET /corpus/*`) — reads `backend/data/pool_all_categories.csv`
  (per-tool F/A/I/R/composite, already on the unified 0-1 scale, 2,784
  knowledge graphs across **all 11 LOD sub-cloud categories**: blod
  (1,301), life-sciences (360), linguistic (249), che-cloud (194),
  government (195), publications (149), social-networking (97),
  cross-domain (83), user-generated (72), geography (47), media (37) —
  every category, including che-cloud, scored by all three tools — see
  `backend/data/build_pool_all_categories.py` for how it's built) and
  `backend/data/kg_repository_map.csv` (id -> source repository, BLOD rows
  only). One page, one combined **source dropdown** — every category
  (including che-cloud) alongside BLOD's individual source repositories
  (Bio2RDF, BioPortal, GitHub, LOD Cloud, Ontobee, Wikidata, OBO Foundry,
  LOV, OLS, Kaggle, Isolated), grouped into two `<optgroup>`s rather than
  two separate pages or dropdowns. Nothing here calls F-UJI, FAIR-Checker,
  or KGHeartBeat live — it's a fast, searchable/paginated browse of what's
  already known, loaded once per backend process and cached in memory.
  Each row expands to full per-metric detail, consensus, and an AI
  explanation.

  che-cloud is scored here from `data/raw/{fuji,fairchecker,kgheartbeat}/
  che-cloud.csv` — the same three-tool assessment run for every category —
  through the exact same mapping pipeline as everything else, so its rows
  get real per-tool composites and a real cross-tool consensus/agreement
  level just like any other category. CheCLOUD's own separately-published,
  KGHeartBeat-only numbers (`backend/data/checloud_fair_scores.csv` /
  `backend/checloud.py`, from the CHe-CLOUD project) remain available via the legacy
  `GET /checloud/*` endpoints for anyone who specifically wants CheCLOUD's
  own published methodology rather than this app's unified mapping.
- **New Assessment** (`POST /assess`) — the live, three-tool path described
  above, for a resource not already in the corpus.
- **Snapshots** (`GET /snapshots/*`) — timestamped, downloadable archives of
  the corpus assessment, one `.zip` per run, mirroring KGHeartBeat's own
  periodic public analysis-data archive (same
  idea: dated files, newest first, downloadable). A monthly snapshot is
  scheduled automatically (APScheduler, in-process, 1st of the month at
  03:00 UTC — see `main.py`'s `lifespan`). There is intentionally no
  on-demand "run now" endpoint or live-catalog-fetch endpoint any more —
  both were unauthenticated ways to trigger expensive live third-party API
  calls on request, so snapshots are produced only by the monthly schedule.
  Each `.zip` contains a CSV of every dataset's
  scores plus a `manifest.json` recording exactly which sources were
  included, split into "full assessment" vs. "catalog-only" vs. "not
  connected" (see the data-sources table below). **Scope note**: this
  module predates the LOD Cloud page's expansion to 11 categories and
  currently only covers BLOD (1,301, from `pool_BLOD_1301.csv`) plus
  CheCLOUD's own published numbers (190, from `checloud.py`) — 1,491 rows
  per snapshot — not the other 9 categories or che-cloud's three-tool
  scores now shown on the LOD Cloud page. Extending `backend/snapshots.py`
  to snapshot the full `pool_all_categories.csv` corpus is a reasonable
  next step, not yet done.
- **FAIR Mapping** (`GET /mapping/reference`) — reference page showing which
  raw metric each tool (F-UJI, FAIR-Checker, KGHeartBeat) contributes to
  each FAIR sub-principle, and the Eq. 1-4 formulas used to aggregate
  everything into the F/A/I/R/FAIR composite shown on every other page,
  plus the consensus agreement formula. Sourced live from
  `mapping/unified_mapping_base.py` — it can never show something the app
  doesn't actually compute.

LOD Cloud, New Assessment, and Snapshots all reuse the exact same
`aggregation/consensus.py` function and the exact same
`ToolScoreView`/`ConsensusView`/`AIExplanation` React components, so
"agreed upon by the tools" means identically the same computation
everywhere in the app — che-cloud rows included, since they carry real
per-tool scores like every other category.

### Data sources: what's actually connected today

`GET /snapshots/sources` (and the Snapshots page) reports this honestly,
at three status levels rather than a flat yes/no:

| Source | Status | Notes |
|---|---|---|
| **LOD Cloud (11 categories)** | ✅ Full assessment | 2,784 KGs, three tools each (F-UJI/FAIR-Checker/KGHeartBeat): blod (1,301, spanning LOD Cloud, GitHub, BioPortal, Wikidata, Bio2RDF, Kaggle, OLS, Ontobee, OBO Foundry, NCBI — see the repository breakdown on the page), che-cloud (194), life-sciences (360), linguistic (249), government (195), publications (149), social-networking (97), cross-domain (83), user-generated (72), geography (47), media (37). CheCLOUD's own separately-published KGHeartBeat-only numbers are also available via `GET /checloud/*` for anyone who wants that project's own methodology specifically. |
| **OBO Foundry** | 🔵 Catalog only | Verified end-to-end, including a live call from this codebase (267 ontologies). |
| **GitHub** | 🔵 Catalog only | Verified end-to-end, including a live call from this codebase. |
| **OLS, NCBI, Ontobee** | 🔵 Catalog only | Endpoint and response shape confirmed real via independent verification, but calling them from the development sandbox this was built in returned HTTP 403 (likely sandbox-IP-specific — the same pattern hit earlier with FAIR-Checker). Unconfirmed from a real deployment. |
| **Wikidata** | 🔵 Catalog only | Endpoint confirmed real; not fetched live (needs a specific SPARQL query per call, no flat listing endpoint). |
| **BioPortal, Kaggle** | ⛔ Not connected | Need your own API credentials (`BIOPORTAL_API_KEY`, `KAGGLE_USERNAME`/`KAGGLE_KEY`). |
| **LOD Cloud** | ⛔ Not connected | The real data source (`lod-cloud.net/lod-data.json`) is documented, but the site's `robots.txt` disallows automated fetching — respected rather than worked around. |
| **Bio2RDF** | ⛔ Not connected | Per-dataset URL convention already used elsewhere in this codebase, but no catalog *listing* endpoint was confirmed. |

"Full assessment" means every entry carries real per-tool FAIR scores and
is included in snapshot data. "Catalog only" means a live, verified
connection can report current size/sample entries via
`GET /snapshots/live-catalogs`, but individual entries are **not** run
through the FAIR tools — doing that for e.g. OLS's 280+ ontologies or
NCBI's millions of records on every snapshot would be an extremely heavy
operation most of these services weren't designed for.

`backend/discovery.py` documents exactly what was verified for each source
and how, including a real (but independently unconfirmed) implementation
of CheCLOUD's own live per-dataset lookup
(KGHeartBeat's public `/kgheartbeat-api/fairness/{id}` endpoint, set via
`KGHEARTBEAT_FAIRNESS_URL`; confirmed present
in CheCLOUD's real backend source code). Nothing in this app claims a
source is live unless it was actually verified against the real endpoint.

## Mapping and consensus logic

`backend/mapping/unified_mapping_base.py` is the tested normalisation layer
(metric → principle → dimension → composite, unweighted mean at each step)
— reused directly from a separately-verified module, not rewritten for this
build. `unified_mapping.py` wraps it to additionally extract each tool's
**native** score (its own reported FAIR value, in its own units) alongside
the **mapped** one, keeping the two explicitly separate per the spec.

`aggregation/consensus.py` computes the cross-tool consensus **on mapped
scores only** (native scores from different tools are not on a comparable
scale and averaging them directly would be meaningless) and labels
agreement `high` / `medium` / `low` based on how far the tools' scores
actually spread apart, not just their absolute level.
