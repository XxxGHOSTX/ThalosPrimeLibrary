#!/usr/bin/env python3
"""Run the Thalos Prime server."""

import sys

import uvicorn

from configs.config import get_settings


def main() -> None:
    """Run the server."""
    settings = get_settings()

    print(f"Starting Thalos Prime server on {settings.host}:{settings.port}")
    print(f"Open http://localhost:{settings.port} in your browser")

    try:
        uvicorn.run(
            "src.api:app",
            host=settings.host,
            port=settings.port,
            reload=False,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
