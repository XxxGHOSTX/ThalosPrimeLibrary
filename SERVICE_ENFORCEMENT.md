# Thalos Prime Service Enforcement (No Restart/No Shutdown)

Use these instructions when you want the service to remain up continuously and **not automatically restart** unless you explicitly intervene.

## Windows (keep running without auto-restart)
1. Start normally (no keep-alive loop):
   ```cmd
   python run_thalos.py
   ```
2. Keep the terminal window open. Do **not** close it; this keeps the service alive.
3. To prevent accidental closure:
   - Disable sleep/hibernation on the machine while running.
   - Keep the console window in the foreground or minimized, but not closed.
4. If you need unattended operation without restarts, use a Windows service (e.g., `nssm`) configured **without** auto-restart:
   - Install NSSM, then set App Path to `python`, Arguments to `run_thalos.py`, Startup directory to the project root.
   - In the NSSM UI, disable automatic restart and set “No action” on exit.

## Policy (Operational)
- Do not run `run_thalos_keepalive.bat` if you do not want restarts.
- Run only one instance at a time to avoid port conflicts (8000/8001).
- Avoid closing the terminal; stopping the process will shut down the service.

## Quick Checks
- To verify it’s up: open `http://127.0.0.1:8000/api/status` in a browser.
- To check port use: `netstat -ano | findstr :8000`

## Notes
- Auto-restart is disabled by simply not using the keep-alive script.
- If you later need auto-restart, use `run_thalos_keepalive.bat`; otherwise, stick to `python run_thalos.py`.

