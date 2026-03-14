# THALOS PRIME - QUICK REFERENCE

## Launch Commands

### Windows
```cmd
run_thalos.bat
```

### Mac/Linux
```bash
bash run_thalos.sh
```

### Direct (All Platforms)
```bash
python run_thalos.py
```

## Access

```
Browser: http://127.0.0.1:8000/
```

## Example Queries

### In Matrix Console
```
Thalos Prime created by Tony Ray Macier III
```

### Direct API
```bash
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Thalos Prime","max_results":3}'
```

## Response Format

```
BABEL_RESPONSE:
QUERY: [your query]
- https://libraryofbabel.info/book.cgi?hex=... SCORE=85
  [snippet from page]
- https://libraryofbabel.info/book.cgi?hex=... SCORE=72
  [snippet from page]
```

## Coherence Scores

| Score | Meaning |
|-------|---------|
| 80-100 | Highly coherent, meaningful content |
| 60-79 | Moderately coherent, recognizable patterns |
| 40-59 | Sparse coherence, mostly noise |
| 0-39 | Minimal coherence, random characters |

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Matrix Console UI |
| `/chat` | POST | Chat interface |
| `/api/search` | POST | Advanced search |
| `/api/status` | GET | Server status |

## Request Examples

### Chat
```json
{
  "message": "your query",
  "session_id": "optional-uuid"
}
```

### Search
```json
{
  "query": "search term",
  "max_results": 5
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Server auto-fallback to 8001, or restart |
| No results | Try simpler terms, wait 1-2 min, check internet |
| Slow response | First query is cached for 1 hour, repeat queries are instant |
| Server won't start | Check Python 3.7+, run `pip install -r requirements.txt` |

## Key Files

| File | Purpose |
|------|---------|
| `run_thalos.py` | Startup script |
| `src/api/__init__.py` | FastAPI server + Matrix UI |
| `src/lob_babel_search.py` | Library of Babel client |
| `src/lob_shard_manager/` | Data sharding system |
| `INSTALLATION_GUIDE.md` | Full setup documentation |
| `ARCHITECTURE.md` | Technical system design |

## Keyboard Shortcuts (Matrix Console)

- `Enter` - Send message
- `Ctrl+A` - Select all text
- `Ctrl+C` (in terminal) - Stop server
- `Ctrl+Z` then `Y` (in terminal, Windows) - Exit

## Environment

- **Python**: 3.7+
- **Memory**: 100-500 MB
- **Storage**: 200 MB
- **Network**: HTTP access to libraryofbabel.info
- **Port**: 8000 (or 8001 fallback)

## Session Management

- Sessions are stored in-browser memory
- Session ID is stored in localStorage
- Conversation history: Last 40 messages (20 exchanges)
- Cache duration: 1 hour per query

## Performance Targets

- Cold query: 2-5 seconds
- Cached query: <100ms
- UI response: Instant
- Max concurrent users: 10+ (depends on Library site)

## Features

✓ Matrix-style UI with real-time chat
✓ Server-side Library of Babel search
✓ Coherence scoring (0-100)
✓ Response caching (1-hour TTL)
✓ Session management
✓ REST API endpoints
✓ Cross-platform startup

## Limitations

- Library of Babel must be accessible
- No persistent storage (in-memory only)
- Max 5 results per query (configurable)
- Sentence-level accuracy varies

## Patent Info

Thalos Prime implements:
- Recursive coherence extraction
- Stabilization and synthesis
- Cross-domain translation
- High-entropy information processing
- Optional biological substrate support

## Support

See `INSTALLATION_GUIDE.md` for detailed troubleshooting.

---

**v1.0 - Matrix Console**
Ready for operation.

