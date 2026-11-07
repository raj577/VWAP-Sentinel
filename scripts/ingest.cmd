@echo off
setlocal
cd /d "%~dp0.."

if not exist logs mkdir logs

set "DATABASE_URL=postgresql+psycopg://avwap:avwap@127.0.0.1:5432/avwap"
set "ENVIRONMENT=development"
set "LOG_LEVEL=INFO"

".venv-backend\Scripts\python.exe" -m backend.cli.ingest --triggered-by cli
