"""Fail-closed bearer-token authentication for Thalos Prime HTTP APIs."""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Require an explicitly configured bearer token at least 32 UTF-8 bytes long."""
    expected = os.environ.get("THALOS_API_TOKEN", "")
    if len(expected.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=503,
            detail="Protected API is unavailable until a strong THALOS_API_TOKEN is configured",
        )

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Bearer authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, separator, supplied = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not hmac.compare_digest(supplied, expected)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
