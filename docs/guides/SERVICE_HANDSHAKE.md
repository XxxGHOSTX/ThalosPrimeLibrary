# Thalos Prime Handshake & Communication Integrity

Use this to verify the line is open and the service is responding coherently.

## Heartbeat / Handshake
- Endpoint: `GET /health`
- Response example:
  ```json
  {"status": "healthy", "version": "0.1.0"}
  ```
- Interpretation: `status=healthy` confirms the service loop is alive.

## Keep Service Running (No Restart)
- Start normally (no auto-restart):
  ```cmd
  python run_thalos.py
  ```
- Keep the terminal open; disable sleep/hibernation while running.
- Do **not** use `run_thalos_keepalive.bat` if you do not want restarts.

## Communication Integrity
- Check `/api/v1/status` and `/health` before sending workloads.
- Use `/api/v1/search/` with explicit query payloads for deterministic behavior.
- For long sessions, send a handshake every few minutes to confirm connectivity.

## Coherent Responses
- Use `/api/v1/search/` or `/api/v1/decode/` for scored, structured replies.
- Include `mode` when needed:
  ```json
  {"query": "your phrase", "mode": "local"}
  ```
- For normalization (optional):
  ```json
  {"query": "your phrase", "pages": [...], "normalize": true}
  ```

## Quick Checks
- Service up: `http://127.0.0.1:8000/health`
- Status: `http://127.0.0.1:8000/api/v1/status`
- Port in use: `netstat -ano | findstr :8000`

## Notes
- Avoid running multiple instances; use one service per port.
- If you need uninterrupted operation, keep the console open and disable system sleep.

