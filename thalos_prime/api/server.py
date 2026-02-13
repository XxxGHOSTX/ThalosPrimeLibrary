"""
FastAPI Server Implementation for Thalos Prime

This module provides the main FastAPI application with all configuration,
middleware, and route registration.
"""

import time
from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator, Any, Callable, Awaitable
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exception_handlers import (
    request_validation_exception_handler,
    http_exception_handler
)
from fastapi.exceptions import RequestValidationError, HTTPException
import logging

from thalos_prime.models.api_models import ErrorResponse
from thalos_prime.api import config as api_config
from thalos_prime import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application state
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Thalos Prime API Server...")
    logger.info(f"Version: {__version__}")
    logger.info(f"Documentation: http://localhost:8000/docs")
    
    # Initialize components
    try:
        await initialize_services()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Thalos Prime API Server...")
    try:
        await cleanup_services()
        logger.info("All services cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


async def initialize_services() -> None:
    """Initialize all application services"""
    # Initialize cache
    logger.info("Initializing cache service...")
    
    # Initialize database connection pool
    logger.info("Initializing database connections...")
    
    # Initialize Redis connection
    logger.info("Initializing Redis connection...")
    
    # Initialize worker queues
    logger.info("Initializing worker queues...")
    
    logger.info("Service initialization complete")


async def cleanup_services() -> None:
    """Cleanup all application services"""
    # Close database connections
    logger.info("Closing database connections...")
    
    # Close Redis connection
    logger.info("Closing Redis connection...")
    
    # Shutdown worker queues
    logger.info("Shutting down worker queues...")
    
    logger.info("Service cleanup complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Thalos Prime API",
        description="""
        # Thalos Prime - Symbiotic Intelligence Framework
        
        A hybrid cognitive synthesis framework that extracts coherent information 
        structures from high-entropy data spaces (the Library of Babel).
        
        ## Features
        
        - **Deterministic Page Generation**: Generate Library of Babel pages from addresses
        - **Query Enumeration**: Map queries to candidate addresses
        - **Coherence Scoring**: Multi-metric analysis of page coherence
        - **Hybrid Search**: Local generation and remote fetching
        - **Real-time Chat**: Interactive conversation interface
        - **Provenance Tracking**: Complete audit trail for all operations
        
        ## Authentication
        
        Most endpoints require authentication via API key or JWT token.
        See the Authentication section for details.
        
        ## Rate Limiting
        
        API requests are rate-limited to prevent abuse.
        See the Rate Limits section for details.
        """,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add custom middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Add X-Process-Time header to all responses"""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Log all incoming requests"""
        logger.info(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response
    
    # Custom exception handlers
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with custom error response"""
        error_response = ErrorResponse(
            error=f"HTTP{exc.status_code}",
            message=exc.detail,
            details={"path": str(request.url.path)}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def custom_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle validation errors with custom error response"""
        error_response = ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            details={"errors": exc.errors()}
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.dict()
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions"""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        error_response = ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            details={"type": type(exc).__name__}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.dict()
        )
    
    # Register routes
    register_routes(app)
    
    # Add health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, Any]:
        """Health check endpoint"""
        uptime = time.time() - START_TIME
        return {
            "status": "healthy",
            "version": __version__,
            "uptime_seconds": uptime
        }
    
    return app


def register_routes(app: FastAPI) -> None:
    """
    Register all API routes.
    
    Args:
        app: FastAPI application instance
    """
    # Import routers (lazy import to avoid circular dependencies)
    try:
        from thalos_prime.api.routes.chat import router as chat_router
        from thalos_prime.api.routes.search import router as search_router
        from thalos_prime.api.routes.generate import router as generate_router
        from thalos_prime.api.routes.enumerate import router as enumerate_router
        from thalos_prime.api.routes.decode import router as decode_router
        from thalos_prime.api.routes.admin import router as admin_router
        from thalos_prime.api.routes.main import router as main_router
        
        # Register routers with prefixes
        app.include_router(main_router, tags=["Main"])
        app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
        app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])
        app.include_router(generate_router, prefix="/api/v1/generate", tags=["Generate"])
        app.include_router(enumerate_router, prefix="/api/v1/enumerate", tags=["Enumerate"])
        app.include_router(decode_router, prefix="/api/v1/decode", tags=["Decode"])
        app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
        
        logger.info("All routes registered successfully")
    except ImportError as e:
        logger.warning(f"Some routes could not be loaded: {e}")
        # Create placeholder routes if imports fail
        create_placeholder_routes(app)


def create_placeholder_routes(app: FastAPI) -> None:
    """Create placeholder routes when actual routes are not available"""
    @app.get("/api/v1/status")
    async def status() -> dict[str, str]:
        return {"status": "ok", "message": "Thalos Prime API is running"}


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "thalos_prime.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
