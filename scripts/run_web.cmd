@echo off
setlocal
cd /d "%~dp0..\frontend"

if not exist ..\logs mkdir ..\logs

node "node_modules\next\dist\bin\next" start -p 3000 > ..\logs\web.out.log 2> ..\logs\web.err.log
