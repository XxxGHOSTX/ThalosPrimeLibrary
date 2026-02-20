"""Thalos Prime API Module.

This module provides the FastAPI REST server implementation for Thalos Prime,
including all endpoints for search, generation, enumeration, and decoding.
"""

from thalos_prime.api.routes import (
    admin_router,
    chat_router,
    decode_router,
    enumerate_router,
    generate_router,
    search_router,
)
from thalos_prime.api.routes import router as main_router
from thalos_prime.api.server import app, create_app

__all__ = [
    "admin_router",
    "app",
    "chat_router",
    "create_app",
    "decode_router",
    "enumerate_router",
    "generate_router",
    "main_router",
    "search_router",
]
