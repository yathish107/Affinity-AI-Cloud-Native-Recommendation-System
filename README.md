# Affinity — Explainable Hybrid Recommendation Platform v2

PostgreSQL is authoritative. Redis caches versioned recommendations. Redpanda carries an at-least-once transactional outbox stream. Separate API, recommendation, relay and consumer processes run with the static frontend. User identities are demo profiles, not authenticated accounts.

## Windows quick start
1. Install/open Docker Desktop using Linux containers.
2. Extract this ZIP and open PowerShell in the project folder.
3. Copy `.env.example` to `.env`. Set long random ADMIN_KEY and GRAFANA_PASSWORD values locally. Never share this file.
4. Run `./run-project.bat` or `docker compose up --build -d`.
5. Open http://localhost:8080. API docs: http://localhost:8000/docs.
6. Stop safely with `./stop-project.bat`. It stops containers and preserves data. Never use down -v on application data.

Monitoring: `docker compose --profile monitoring up -d`. Grafana: http://localhost:3000 (admin and configured password); Prometheus: http://localhost:9090. To enable traces also set OTEL_EXPORTER_OTLP_ENDPOINT=http://otel:4318 in .env and recreate API services. The collector exports traces to its logs.

The catalog is the original 12-product catalog. Counts, recommendations, history and service status come from live backend requests. Empty data shows an honest cold start. The old interface is retained at /legacy.html for compatibility, though its score display does not show new explanations.

## Model
TF-IDF user-profile cosine + implicit item-item collaborative cosine + distinct-user popularity. Collaborative pairs require two supporting users. Available components are normalized from 0.6/0.3/0.1 weights. Previously interacted products are excluded. Numeric component contributions sum to ranking score. Scores are not purchase probabilities. Collaborative/global popularity reflects processed events; content uses accepted canonical history immediately. Decay and neural embeddings are not implemented.

## Verification
See docs/FINAL_IMPLEMENTATION_REPORT.md for actual checks and limitations. No live Docker/PostgreSQL/Redis/Redpanda/Kubernetes verification was performed here. New UI syntax was checked; the 21 frontend behavioural checks cover retained legacy UI, not browser validation of the new UI.
Run `python -m pytest backend/tests -q` after installing runtime and development requirements. Live tests use the isolated compose.integration.yml; see docs/PHASE2_WINDOWS_VERIFICATION.md. Do not run destructive integration tests against application databases.

## Evaluation and load testing
Export real canonical events to a JSON array with event_id,user_id,product_id,event_type,dwell_seconds,created_at. Run `python scripts/evaluate.py events.json --cutoff 2026-11-01T00:00:00+00:00 --output evaluation.json`. The cutoff must precede held-out events in your data. Metrics are Precision@K, Recall@K and NDCG@K; no dataset is fabricated.
Install scripts' development requirements and run `powershell -File scripts/benchmark.ps1`. Locust sends real load and creates real events; use a disposable deployment. Outputs are benchmark CSV and HTML. No live throughput or latency values are included because no infrastructure benchmark was executed.

## API
GET /products; POST /events; GET /events/{user_id}; GET /recommendations/{user_id}?limit=5; GET /trending; GET /system; GET /admin/analytics (X-Admin-Key); GET /health, /live, /ready, /metrics. nginx exposes these under /api. A stable event_id UUID is required for deduplicated retries; omitted IDs are generated per request. A reused ID with different payload returns 409. Event acceptance is returned after commit; publication is asynchronous. Admin key is held only in the page input and not persisted.

Kubernetes instructions: k8s/README.md. Migration/rollback: docs/MIGRATION.md. Original phase reports remain historical records, not current deployment instructions.

## Affinity frontend upgrade (4 November 2026)

The existing frontend now includes locally bundled product photographs, redesigned Discover, activity pagination/filtering, real-data analytics charts and explicit dependency status cards. No backend or deployment configuration changed. See [the frontend upgrade report](docs/FRONTEND_UPGRADE_REPORT.md) for actual test results, limitations, source attribution and exact Windows rebuild commands.

For an already-running installation, retain the existing project directory and `.env`, update its frontend files, then run `docker compose build frontend` followed by `docker compose up -d --no-deps frontend`. Hard-refresh http://localhost:8080. Source image edits require `python frontend/tools/bundle_images.py` before rebuilding; the delivered bundle is already generated.
