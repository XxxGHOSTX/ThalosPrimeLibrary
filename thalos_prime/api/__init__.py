"""
Thalos Prime API Module

This module provides the FastAPI REST server implementation for Thalos Prime,
including all endpoints for search, generation, enumeration, and decoding.
"""

from thalos_prime.api.server import app, create_app
from thalos_prime.api.routes import (
    router as main_router,
    chat_router,
    search_router,
    generate_router,
    enumerate_router,
    decode_router,
    admin_router
)

__all__ = [
    'app',
    'create_app',
    'main_router',
    'chat_router',
    'search_router',
    'generate_router',
    'enumerate_router',
    'decode_router',
    'admin_router',
]
