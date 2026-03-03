"""Communication protocol definitions for Babel API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RequestProtocol(BaseModel):
    """Request protocol for Babel API."""

    session_id: str
    user_input: str
    context: dict[str, Any] | None = None


class ResponseProtocol(BaseModel):
    """Response protocol for Babel API."""

    text: str
    coordinate: str
    template_id: str
    semantic_preserved: bool
    coherent: bool
    metadata: dict[str, Any]
