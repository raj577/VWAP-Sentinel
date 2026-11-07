@echo off
setlocal
cd /d "%~dp0.."

if not exist logs mkdir logs
if not exist .tmp mkdir .tmp

set "DATABASE_URL=postgresql+psycopg://avwap:avwap@127.0.0.1:5432/avwap"
set "ENVIRONMENT=development"
set "LOG_LEVEL=INFO"
set "CORS_ORIGINS=http://localhost:3000,http://localhost:8501"
set "ADMIN_API_KEY=dev-admin-key"
set "FYERS_BACKEND_REDIRECT_URI=http://localhost:8000/api/v1/fyers/callback"
set "FRONTEND_BASE_URL=http://localhost:3000"

".venv-backend\Scripts\pythonw.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > logs\api.out.log 2> logs\api.err.log

