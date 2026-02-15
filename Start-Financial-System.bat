@echo off
set "ROOT=%~dp0"
cd /d "%ROOT%"
title Stock Trader - Setup and Run

:: Find Python (Windows often has 'py' launcher or 'python')
set PYTHON=
where py >nul 2>nul && set PYTHON=py -3
if not defined PYTHON where python >nul 2>nul && set PYTHON=python
if not defined PYTHON (
    echo.
    echo Python was not found. Please install Python 3.10 or newer.
    echo.
    echo Opening the Python download page...
    echo After installing, add Python to PATH, then run this file again.
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found.
echo.

:: Create virtual environment if it doesn't exist
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment - first run only...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Done.
    echo.
)

:: Use venv Python for the rest
set VENV_PY=.venv\Scripts\python.exe
set VENV_PIP=.venv\Scripts\pip.exe

:: Install or update dependencies
echo Installing dependencies...
"%VENV_PY%" -m pip install --upgrade pip -q
"%VENV_PIP%" install -r requirements.txt -q
if errorlevel 1 (
    echo Failed to install dependencies. Run: pip install -r requirements.txt
    pause
    exit /b 1
)
echo Dependencies OK.
echo.

:: Start the web server in a new window
echo Starting web server...
start "Stock Trader Web" call "%ROOT%_run_server.bat"
timeout /t 3 /nobreak > nul

:: Open browser
start http://localhost:5000
echo.
echo Browser opened at http://localhost:5000
echo The server is running in the other window. Close that window to stop the server.
echo.
pause
