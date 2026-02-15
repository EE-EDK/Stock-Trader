@echo off
cd /d "%~dp0"
start "Stock Trader Web" cmd /k "uvicorn web.main:app --host 0.0.0.0 --port 5000"
timeout /t 2 /nobreak > nul
start chrome http://localhost:5000
