@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m uvicorn web.main:app --host 0.0.0.0 --port 5000
pause
