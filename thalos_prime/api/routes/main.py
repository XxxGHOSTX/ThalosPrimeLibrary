"""Main Routes - Root endpoints and UI/static serving."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, Response

router = APIRouter()

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[3]
_UI_TEMPLATE_INDEX = _REPO_ROOT / "thalos_prime" / "ui" / "templates" / "index.html"


@router.get("/", response_class=HTMLResponse)
async def root() -> Response:
    """Serve the main UI page.

    Returns the Matrix-style interface for Thalos Prime.
    """
    if _UI_TEMPLATE_INDEX.exists():
        return FileResponse(path=str(_UI_TEMPLATE_INDEX), media_type="text/html")

    # Return basic HTML if file doesn't exist
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Thalos Prime</title>
        <style>
            body {
                background: #000;
                color: #0f0;
                font-family: 'Courier New', monospace;
                padding: 50px;
                text-align: center;
            }
            h1 { font-size: 48px; margin-bottom: 20px; }
            p { font-size: 18px; }
            a { color: #0f0; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>THALOS PRIME</h1>
        <p>Symbiotic Intelligence Framework</p>
        <p><a href="/docs">API Documentation</a></p>
        <p><a href="/api/v1/status">API Status</a></p>
    </body>
    </html>
    """)


@router.get("/api/v1/status")
async def api_status() -> dict[str, Any]:
    """Get API status.

    Returns basic information about the API availability.
    """
    return {
        "status": "online",
        "message": "Thalos Prime API is operational",
        "endpoints": {
            "docs": "/docs",
            "chat": "/api/v1/chat",
            "chat_high_coherence": "/api/v1/chat/high_coherence",
            "sense_query": "/api/v1/sense/query",
            "search": "/api/v1/search",
            "generate": "/api/v1/generate",
            "enumerate": "/api/v1/enumerate",
            "decode": "/api/v1/decode",
            "ingest": "/api/v1/artifacts/ingest",
            "artifact": "/api/v1/artifacts/artifact/{artifact_id}",
            "derive": "/api/v1/artifacts/derive",
            "export": "/api/v1/artifacts/export/{artifact_id}",
            "graph": "/api/v1/artifacts/graph/{artifact_id}",
            "consensus": "/api/v1/artifacts/consensus",
        },
    }
