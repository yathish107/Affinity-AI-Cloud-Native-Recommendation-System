@echo off
cd /d "%~dp0"
if not exist .env (
  echo Copy .env.example to .env and set ADMIN_KEY and GRAFANA_PASSWORD first.
  exit /b 1
)
docker compose up --build -d
if errorlevel 1 exit /b 1
echo Open http://localhost:8080
