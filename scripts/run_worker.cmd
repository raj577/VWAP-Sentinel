@echo off
setlocal
cd /d "%~dp0.."

if not exist logs mkdir logs

set "DATABASE_URL=postgresql+psycopg://avwap:avwap@127.0.0.1:5432/avwap"
set "ENVIRONMENT=development"
set "LOG_LEVEL=INFO"

".venv-backend\Scripts\pythonw.exe" -m backend.worker_main > logs\worker.out.log 2> logs\worker.err.log
