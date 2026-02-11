@echo off
REM Thalos Prime One-Click Server Only (no monitor, no restart)
cd /d "%~dp0"
start "Thalos Prime Server" cmd /k "python run_thalos.py"
echo Thalos Prime server starting... keep the server window open.
echo Window: "Thalos Prime Server"
echo.
pause

