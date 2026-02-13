"""
Main Routes - Root endpoints

Provides the main landing page and UI serving.
"""

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse, FileResponse
from typing import Any
import os

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """
    Serve the main UI page.
    
    Returns the Matrix-style interface for Thalos Prime.
    """
    # Check if index.html exists in root
    index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "index.html")
    
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            return HTMLResponse(content=f.read())
    
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
    """
    Get API status.
    
    Returns basic information about the API availability.
    """
    return {
        "status": "online",
        "message": "Thalos Prime API is operational",
        "endpoints": {
            "docs": "/docs",
            "chat": "/api/v1/chat",
            "search": "/api/v1/search",
            "generate": "/api/v1/generate",
            "enumerate": "/api/v1/enumerate",
            "decode": "/api/v1/decode"
        }
    }
