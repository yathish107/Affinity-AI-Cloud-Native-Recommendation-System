# Windows Docker Desktop verification
Status: instructions and test environment prepared; not executed in the authoring environment. Use Linux containers in Docker Desktop. Open PowerShell in the extracted project root. The standalone Compose file uses a separate project, no host ports, no application volumes and a disposable tmpfs PostgreSQL test database. Tests deliberately truncate only recommend_integration.

```powershell
docker version
docker compose version
docker compose -p recommendation-phase2-tests -f compose.integration.yml config
docker compose -p recommendation-phase2-tests -f compose.integration.yml build tests
docker compose -p recommendation-phase2-tests -f compose.integration.yml up -d postgres redis broker topics
docker compose -p recommendation-phase2-tests -f compose.integration.yml run --rm tests
$testExit = $LASTEXITCODE
Write-Host "Integration exit code: $testExit"
docker compose -p recommendation-phase2-tests -f compose.integration.yml logs --no-color postgres redis broker topics | Out-File -Encoding utf8 phase2-service-logs.txt
```
Expected (not observed here): four live recovery tests pass, exit 0. Tests apply Alembic migrations, inject outbox constraint failure, race 12 claimers, simulate process failure after an actual broker acknowledgment, close/reopen a real consumer before offset commit, and stop Redis with SHUTDOWN before its test-only supervisor restarts it. Redis fallback test exercises database snapshot availability; it is not an end-to-end HTTP fallback test. Relay crash is an injected exception, not an OS kill.

Optional existing integration suite, after the above tests:
```powershell
docker compose -p recommendation-phase2-tests -f compose.integration.yml run --rm -e TEST_REDIS_URL=redis://redis:6379/0 tests sh -c 'alembic upgrade head && python -m pytest tests/test_phase2_integration.py -v -ra'
```
The existing lease test needs an empty outbox; use a fresh disposable test project before that optional suite. Main four-test suite cleans its own dedicated tables.

After saving logs, stop only this test environment:
```powershell
docker compose -p recommendation-phase2-tests -f compose.integration.yml down
```
Never add -v to normal application commands. Never run tests against application DATABASE_URL. No host Docker socket is mounted. Broker data may be in an image-created anonymous volume: inspect test-project volumes before manually removing anything; no automatic volume deletion is supplied.

Diagnostics:
- Docker daemon unavailable: open Docker Desktop, select Linux containers, wait for engine readiness; retry docker version.
- Image/package download failure: retain build log; verify internet/proxy access. Image builds were not tested here.
- postgres unhealthy: inspect postgres logs, memory/disk allocation; pg_isready must succeed before migration.
- broker unhealthy: inspect broker logs and Docker resource allocation; no need to expose port 9092 on the host.
- topics failure on rerun: inspect rpk output; the topic init must confirm user-events exists. Restart only the test project if state is stale.
- migration error: capture full traceback; do not stamp over it or drop production tables.
- rollback test fails: check that test_fail constraint is removed in its finally block before retrying.
- no broker events: inspect topics and broker metadata reachability inside Compose; user-events must have one partition.
- Redis recovery timeout: inspect Redis logs; integration supervisor should restart after three seconds.
- any skipped integration test: inspect TEST_DATABASE_URL/INTEGRATION_TEST_MODE; skips do not count as passes.
