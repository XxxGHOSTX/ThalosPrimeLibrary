@echo off
REM Thalos Prime All-in-One Launcher
REM One click: install deps (if needed), start server, start handshake monitor.
cd /d "%~dp0"

REM Install dependencies quietly (skips already installed)
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt >nul 2>&1

REM Start server window
start "Thalos Prime Server" cmd /k "python run_thalos.py"

REM Start handshake monitor window (alerts only, no restart)
start "Thalos Handshake Monitor" powershell -ExecutionPolicy Bypass -File "automation_handshake_monitor.ps1" -IntervalSeconds 60

echo Thalos Prime launched (server + monitor). Keep both windows open.
echo Server: "Thalos Prime Server"
echo Monitor: "Thalos Handshake Monitor" (beeps on failure)
echo.
pause

