@echo off
REM Thalos Prime keep-alive launcher (Windows)
REM Keeps the server running; restarts if it exits.
cd /d "%~dp0"
:loop
  echo [Thalos Keepalive] Starting server at %date% %time%
  python run_thalos.py
  echo [Thalos Keepalive] Server exited with code %errorlevel% at %date% %time%
  echo [Thalos Keepalive] Restarting in 5 seconds... Press Ctrl+C to stop.
  timeout /t 5 /nobreak >nul
goto loop

