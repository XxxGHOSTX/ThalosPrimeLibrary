"""
API Routes Module - Initialization

This module exports all route routers.
"""

from thalos_prime.api.routes.main import router
from thalos_prime.api.routes.chat import router as chat_router
from thalos_prime.api.routes.search import router as search_router
from thalos_prime.api.routes.generate import router as generate_router
from thalos_prime.api.routes.enumerate import router as enumerate_router
from thalos_prime.api.routes.decode import router as decode_router
from thalos_prime.api.routes.admin import router as admin_router

__all__ = [
    'router',
    'chat_router',
    'search_router',
    'generate_router',
    'enumerate_router',
    'decode_router',
    'admin_router',
]
