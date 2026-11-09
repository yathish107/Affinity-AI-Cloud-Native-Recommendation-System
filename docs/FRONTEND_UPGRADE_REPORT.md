# Affinity v2 frontend upgrade — 4 November 2026

## Scope and preservation

Continued the existing source checkpoint. Modified only frontend source, frontend tests and documentation. Backend APIs, recommendation algorithms, database schema, PostgreSQL/Redis/Redpanda integrations, workers, dependency locks, Dockerfiles, Compose and Kubernetes manifests are unchanged. The original ZIP SHA256 remains `d7f15661beb65024c29a4bac4409cab40fe13df30c0deadbae9407be16024ea8`.

Before editing, inspected the complete frontend (HTML, CSS, JavaScript, nginx, Dockerfile, legacy tests and browser test), the backend service routes, catalogue and analytics response. Existing image-free cards used category glyphs. The last four stable catalogue IDs are p9 Desk Lamp, p10 Office Chair, p11 Coffee Maker and p12 Travel Backpack, not the order of the requested product list. All mapping uses IDs.

## Implemented

- Forest-green sidebar, cream canvas, pale-green surfaces, serif headings, local sans-serif system fonts, shared buttons and responsive cards; no external font requests.
- Twelve distinct locally stored product photographs, central ID mapping, consistent image frames, accessible alt text and product-name fallbacks. Reused for catalogue, recommendations and trending. Sources documented in `frontend/assets/products/SOURCES.md` and manifest.
- Discover: welcome/hero, category chips using unchanged backend categories, search, product count, price, View/Click/Purchase actions, “Recommended for you”, backend score and expandable reasons/contributions. Missing scores and explanations are not fabricated.
- Request panels load independently. One unavailable recommendation service no longer prevents catalogue or trending loading. Error, loading and empty states are local to each section.
- Stable per-interaction IDs survive retries within the page session. Duplicate clicks across cards are blocked while a request is pending. The selected profile changes only after Switch is submitted; typing in the field does not silently change event identity. Recommendation/history request generations discard stale responses.
- Activity timeline: names, event icons, local timestamps, page size 50, Previous/Next and current-page event-type filters. Page boundaries rely on returned row count because the API has no total. A final full page can lead to an empty next page; Previous remains available.
- Admin: existing X-Admin-Key header retained; key stays in memory only. Five count cards plus distinct interaction-type count, CSS bar charts from real response fields, no chart library. Demo users means all distinct IDs with events, not recently active authenticated users. Processing counts are independent, not a misleading parts-of-total chart.
- Health: API, PostgreSQL, Redis and recommendation service cards. Only literal `up` is green; `down` is red; unknown/degraded is amber. Refresh failures replace previous statuses with Unknown. No worker or broker health is inferred.
- Keyboard focus, skip link, semantic navigation, native expandable explanations, polite status messages and reduced-motion support. Responsive breakpoints cover mobile/tablet/desktop; browser layout verification remains pending.

## API compatibility

| Function | Existing endpoint and request retained |
|---|---|
| Catalogue | GET /api/products |
| Recommendations | GET /api/recommendations/{encoded user} |
| Event tracking | POST /api/events; event_id, user_id, product_id, event_type, dwell_seconds: 0 |
| History | GET /api/events/{encoded user}?limit=50&offset=N |
| Trending | GET /api/trending |
| Analytics | GET /api/admin/analytics; X-Admin-Key |
| Health | GET /api/system |

Purchase remains an interaction, not a payment or checkout. Events are not automatically retried in the background. The user can retry with the same pending ID. Refreshing the whole browser page discards pending IDs, as in the original implementation. A committed event and a subsequent failed recommendation fetch are reported separately.

## Changed and added files

Modified:
- frontend/index.html
- frontend/style.css
- frontend/app.js
- frontend/browser-tests/test_ui.py (navigation label case aligned with the new UI; existing live smoke test preserved)
- README.md (links to this report and commands)
- docs/FINAL_IMPLEMENTATION_REPORT.md (frontend status addendum)

Added:
- frontend/assets/products/p1.jpg through p12.jpg
- frontend/assets/products/manifest.json
- frontend/assets/products/SOURCES.md
- frontend/tools/bundle_images.py
- frontend/tests/ui.cjs
- frontend/browser-tests/test_frontend_contract.py
- docs/FRONTEND_UPGRADE_REPORT.md
- docs/frontend-upgrade/* (actual logs, environment and integrity evidence)

No new application dependencies. Charts are CSS and HTML; icons are inline SVG constants. The image bundler uses Python standard library. Browser tests use already-declared pytest/Playwright dependencies.

## Actual verification

| Check | Result |
|---|---|
| Node existing legacy tests | 21 passed |
| Node new UI contract tests | 18 passed |
| Combined frontend suite | 39 passed, 0 failed; 475.798977 ms |
| Backend pytest suite | 51 passed, 7 skipped, 4 warnings; 46.17 s |
| JavaScript syntax | Passed |
| Frontend Python source syntax | Passed |
| HTML IDs and JavaScript literal ID references | Passed; no missing/duplicate IDs |
| Product files | All 12 decode as JPEG, distinct SHA256s, embedded bytes match local sources |
| Photograph review | Actual image contact sheet and replacement photos visually inspected |
| Browser suite | Attempted; 1 setup error, 1 warning, stopped at first failure; no UI assertions executed |
| Live Docker / PostgreSQL / Redis / Redpanda / Kubernetes | Not executed |

Browser failure: Chromium `process_singleton_posix.cc` reported `socket() failed: Operation not permitted (1)` and exited. Consequently there is no claim of browser console cleanliness, screenshot/layout verification, or live end-to-end UI verification. Eleven parameterized Playwright cases are provided, with explicit test-only API fixtures covering all pages, photographs, search/filtering, event retries, admin header, health errors, keyboard access and widths 320/390/768/1440. Fixtures are not included in the production app.

Node tests use a minimal DOM fixture, not a rendering engine. They verify request/state and generated DOM contracts. The backend suite ran against available packages after installing missing test dependencies into the temporary environment; this is not certification of a clean locked Docker installation. Exact package versions are in `docs/frontend-upgrade/VALIDATION_ENVIRONMENT.txt`. Existing backend deprecation warnings and the skipped integration tests are retained in the log.

## Windows: rebuild an existing running installation

1. Keep your existing project directory, `.env` and Docker project name so existing named volumes are reused. Back up the current frontend files, then copy the updated `frontend` directory over them.
2. Open Docker Desktop (Linux containers) and PowerShell in that existing project root.
3. Run:

```powershell
docker compose build frontend
docker compose up -d --no-deps frontend
docker compose ps
docker compose logs --tail=50 frontend
```

Open http://localhost:8080 and hard-refresh with Ctrl+F5. These commands are provided, not executed here. Do not use `down -v` or prune volumes.

## Windows: fresh installation

Extract the ZIP and open PowerShell inside `AI_Cloud_Native_Recommendation_Project` (the directory containing docker-compose.yml):

```powershell
# Only create .env if it does not already exist:
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
# Set nonempty ADMIN_KEY and GRAFANA_PASSWORD, save, then:
docker compose up --build -d
docker compose ps
docker compose logs --tail=50 frontend recommender recommendation
```

Open http://localhost:8080. The unchanged `run-project.bat` is an alternative. To stop without deleting data:

```powershell
docker compose stop
```

The photographs are already embedded in app.js, so Python/Node is not needed to rebuild the frontend container. If editing source photographs, run `py frontend/tools/bundle_images.py` before the Docker build.

## Repeat frontend validation on Windows

```powershell
node --test frontend/tests/phase1.cjs frontend/tests/ui.cjs
py -m venv .venv-ui
.\.venv-ui\Scripts\python -m pip install pytest==9.2.0 playwright==1.56.0
.\.venv-ui\Scripts\python -m playwright install chromium
.\.venv-ui\Scripts\python -m pytest frontend/browser-tests/test_frontend_contract.py -q
```

The contract browser suite does not need Docker or live services. After the full stack is running, the existing live smoke test can be run separately:

```powershell
.\.venv-ui\Scripts\python frontend/browser-tests/test_ui.py
```

The live smoke test creates one demo View interaction. If images seem unchanged, rebuild the frontend and hard-refresh. If analytics rejects a key, use the exact ADMIN_KEY from the existing environment. If health is Unknown or a panel cannot load, inspect API and recommendation logs; do not interpret a rendered page as infrastructure health.
