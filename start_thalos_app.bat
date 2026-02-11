@echo off
REM Thalos Prime One-Click Launcher (no auto-restart)
REM Starts the API server and handshake monitor in separate windows.
cd /d "%~dp0"

REM Start Thalos Prime server
start "Thalos Prime Server" cmd /k "python run_thalos.py"

REM Start handshake monitor (alerts only, no restart)
start "Thalos Handshake Monitor" powershell -ExecutionPolicy Bypass -File "automation_handshake_monitor.ps1" -IntervalSeconds 60

echo Thalos Prime launching... keep the windows open.
echo - Server window: "Thalos Prime Server"
echo - Monitor window: "Thalos Handshake Monitor" (beeps on failure)
echo.
pause

