"""
Communication protocol definitions for Babel API.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel


class RequestProtocol(BaseModel):
    session_id: str
    user_input: str
    context: Optional[Dict[str, Any]] = None


class ResponseProtocol(BaseModel):
    text: str
    coordinate: str
    template_id: str
    semantic_preserved: bool
    coherent: bool
    metadata: Dict[str, Any]
