"""Communication protocol definitions for Babel API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RequestProtocol(BaseModel):
    """Pydantic model for incoming API conversation requests."""

    session_id: str
    user_input: str
    context: dict[str, Any] | None = None


class ResponseProtocol(BaseModel):
    """Pydantic model for outgoing API conversation responses."""

    text: str
    coordinate: str
    template_id: str
    semantic_preserved: bool
    coherent: bool
    metadata: dict[str, Any]
