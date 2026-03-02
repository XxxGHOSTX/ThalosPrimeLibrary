"""ASGI entrypoint for Vercel/FastAPI auto-detection."""

from thalos_prime.api.server import app

__all__ = ["app"]
