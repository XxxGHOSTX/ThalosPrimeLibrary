"""Strict CORS allowlist parsing for the Thalos Prime API."""

from __future__ import annotations

import os
from urllib.parse import urlsplit


def get_configured_cors_origins(
    environment: str | None = None,
    raw_origins: str | None = None,
) -> list[str]:
    """Return a validated CORS allowlist; never permit wildcard production CORS."""
    app_environment = (
        environment
        if environment is not None
        else os.getenv("THALOS_ENV", "development")
    ).strip().lower()
    production = app_environment in {"production", "prod"}
    configured = (
        raw_origins
        if raw_origins is not None
        else os.getenv("THALOS_CORS_ORIGINS")
    )

    if configured is None or not configured.strip():
        if production:
            raise ValueError(
                "THALOS_CORS_ORIGINS must be explicitly configured in production"
            )
        configured = "http://localhost:3000,http://127.0.0.1:3000"

    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    if not origins:
        raise ValueError(
            "THALOS_CORS_ORIGINS must contain at least one explicit origin"
        )

    validated: list[str] = []
    for origin in origins:
        if origin == "*":
            raise ValueError(
                "Wildcard CORS origins are prohibited; configure exact origins"
            )

        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(
                "Each CORS origin must be an explicit http:// or https:// origin"
            )
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("CORS origins must not contain user information")
        if parsed.path or parsed.query or parsed.fragment:
            raise ValueError(
                "CORS entries must be origins only, without paths, queries, or fragments"
            )
        try:
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("CORS origin contains an invalid port") from exc

        if production and parsed.scheme != "https":
            raise ValueError("Production CORS origins must use HTTPS")

        validated.append(origin)

    return validated
