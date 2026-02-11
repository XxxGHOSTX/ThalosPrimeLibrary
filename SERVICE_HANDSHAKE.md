# Thalos Prime Handshake & Communication Integrity

Use this to verify the line is open and the service is responding coherently.

## Heartbeat / Handshake
- Endpoint: `GET /api/handshake`
- Response example:
  ```json
  {"status": "open", "mode": "remote", "timestamp": "2026-02-10T00:00:00Z"}
  ```
- Interpretation: `status=open` confirms the service loop is alive; `mode` shows current search path (remote/local).

## Keep Service Running (No Restart)
- Start normally (no auto-restart):
  ```cmd
  python run_thalos.py
  ```
- Keep the terminal open; disable sleep/hibernation while running.
- Do **not** use `run_thalos_keepalive.bat` if you do not want restarts.

## Communication Integrity
- Check `/api/status` and `/api/handshake` before sending workloads.
- Use `/api/search` with `mode` set to `local` or `remote` explicitly to avoid ambiguity.
- For long sessions, send a handshake every few minutes to confirm connectivity.

## Coherent Responses
- Use `/api/search` or `/api/decode` for scored, structured replies.
- Include `mode` when needed:
  ```json
  {"query": "your phrase", "mode": "local"}
  ```
- For normalization (optional):
  ```json
  {"query": "your phrase", "pages": [...], "normalize": true}
  ```

## Quick Checks
- Service up: `http://127.0.0.1:8000/api/handshake`
- Status: `http://127.0.0.1:8000/api/status`
- Port in use: `netstat -ano | findstr :8000`

## Notes
- Avoid running multiple instances; use one service per port.
- If you need uninterrupted operation, keep the console open and disable system sleep.

