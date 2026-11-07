@echo off
setlocal
cd /d "%~dp0.."

if not exist logs mkdir logs

set "DATABASE_URL=postgresql+psycopg://avwap:avwap@127.0.0.1:5432/avwap"
set "ENVIRONMENT=development"
set "LOG_LEVEL=INFO"
set "SCHEDULER_ENABLED=true"
set "SCHEDULER_INTERVAL_MINUTES=56"

".venv-backend\Scripts\pythonw.exe" -m backend.scheduler_main > logs\scheduler.out.log 2> logs\scheduler.err.log
