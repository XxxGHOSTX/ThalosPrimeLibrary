"""ASGI entrypoint for Vercel/FastAPI auto-detection."""

from thalos_prime.api.server import create_app

app = create_app()

__all__ = ["app"]
