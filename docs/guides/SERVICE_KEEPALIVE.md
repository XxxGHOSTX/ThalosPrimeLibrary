# Thalos Prime Keep-Alive

Use this to keep the server running and automatically restart if it exits.

## Windows (preferred)
Run the keep-alive launcher:
```
run_thalos_keepalive.bat
```
- Starts `run_thalos.py`
- Restarts automatically if it exits
- Press Ctrl+C in the window to stop

## Notes
- Ensure Python and dependencies are installed (`pip install -r requirements.txt`).
- Port 8000/8001 must be free; keep-alive will retry after each exit.
- For a clean shutdown, use Ctrl+C once; the loop will stop.

