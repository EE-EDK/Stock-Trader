@echo off
set "ROOT=%~dp0"
cd /d "%ROOT%"
title Stock Trader - Setup and Run

:: Find Python: py launcher, python in PATH, or try after winget install
set PYTHON=
where py >nul 2>nul && set PYTHON=py -3
if not defined PYTHON where python >nul 2>nul && set PYTHON=python

if not defined PYTHON (
    echo.
    echo Python was not found. Attempting to install via Windows Package Manager...
    echo.
    where winget >nul 2>nul && (
        winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
        if errorlevel 1 winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements --silent
    )
    :: Use common install paths after winget (PATH may not be updated in this session)
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    if not defined PYTHON if exist "%ProgramFiles%\Python312\python.exe" set "PYTHON=%ProgramFiles%\Python312\python.exe"
    if not defined PYTHON if exist "%ProgramFiles%\Python311\python.exe" set "PYTHON=%ProgramFiles%\Python311\python.exe"
)

if not defined PYTHON (
    echo Python is still not available.
    echo Opening the Python download page - install Python, add it to PATH, then run this file again.
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found.
echo.

:: Create virtual environment if it does not exist
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment - first run only...
    if not "%PYTHON:\=%"=="%PYTHON%" ("%PYTHON%" -m venv .venv) else (%PYTHON% -m venv .venv)
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Done.
    echo.
)

set VENV_PY=.venv\Scripts\python.exe
set VENV_PIP=.venv\Scripts\pip.exe

:: Install or update dependencies - continue even if something fails so user can retry or run server
echo Installing dependencies...
"%VENV_PY%" -m pip install --upgrade pip -q
"%VENV_PIP%" install -r requirements.txt -q
if errorlevel 1 (
    echo.
    echo Dependency install had errors. You can fix and run again, or try starting the server anyway.
    echo To retry manually: .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
) else (
    echo Dependencies OK.
)
echo.

:: Start the web server in a new window
echo Starting web server...
start "Stock Trader Web" cmd /k "cd /d %ROOT% && .venv\Scripts\python.exe -m uvicorn web.main:app --host 0.0.0.0 --port 5000"
timeout /t 3 /nobreak > nul

:: Open browser
start http://localhost:5000
echo.
echo Browser opened at http://localhost:5000
echo The server is running in the other window. Close that window to stop the server.
echo.
pause
