"""Safe CORS configuration for the Thalos Prime API."""
import os


def get_configured_cors_origins(environment: str | None = None, raw_origins: str | None = None) -> list[str]:
    """Return an explicit CORS origin allowlist and reject unsafe configurations."""
    app_environment = (environment if environment is not None else os.getenv("THALOS_ENV", "development")).strip().lower()
    configured = raw_origins if raw_origins is not None else os.getenv("THALOS_CORS_ORIGINS")
    if configured is None or not configured.strip():
        if app_environment == "production":
            raise ValueError("THALOS_CORS_ORIGINS must be explicitly configured in production")
        configured = "http://localhost:3000,http://127.0.0.1:3000"
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    if not origins:
        raise ValueError("THALOS_CORS_ORIGINS must contain at least one explicit origin")
    if "*" in origins:
        raise ValueError("Wildcard CORS origins are prohibited; configure exact origins")
    if any(not origin.startswith(("https://", "http://")) for origin in origins):
        raise ValueError("Each CORS origin must be an explicit http:// or https:// origin")
    return origins
