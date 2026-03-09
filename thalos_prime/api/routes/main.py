"""Main Routes - Root endpoints.

Provides the main landing page and UI serving.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

# Prefer the UI template over the root index.html
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE_PATH = _PROJECT_ROOT / "thalos_prime" / "ui" / "templates" / "index.html"
_ROOT_INDEX_PATH = _PROJECT_ROOT / "index.html"


def _load_html() -> str:
    """Load HTML content from template or root index file.

    Returns:
        HTML content string.

    """
    # Serve the Thalos Prime UI template if available
    if _TEMPLATE_PATH.exists():
        return _TEMPLATE_PATH.read_text(encoding="utf-8")
    # Fallback to root index.html only if it looks like a proper HTML app
    if _ROOT_INDEX_PATH.exists():
        content = _ROOT_INDEX_PATH.read_text(encoding="utf-8")
        if "DOCTYPE html" in content and "Thalos" in content:
            return content
    return _FALLBACK_HTML


_FALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thalos Prime</title>
    <style>
        body { background: #000; color: #0f0; font-family: 'Courier New', monospace; padding: 50px; text-align: center; }
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
"""


@router.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Serve the main Thalos Prime UI page.

    Returns the Matrix-style interface for Thalos Prime.
    """
    return HTMLResponse(content=_load_html())


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
            "auth": "/api/v1/auth",
            "subscription": "/api/v1/subscription",
            "chat": "/api/v1/chat",
            "search": "/api/v1/search",
            "generate": "/api/v1/generate",
            "enumerate": "/api/v1/enumerate",
            "decode": "/api/v1/decode",
        },
    }
