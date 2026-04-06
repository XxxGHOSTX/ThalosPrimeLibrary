"""Admin Routes - Administrative endpoints.

Provides administrative and monitoring functionality.
"""

import asyncio
import os
import signal
import sys
import time
from typing import Any

import psutil
from fastapi import APIRouter, Depends, Header, HTTPException

from thalos_prime import __version__
from thalos_prime.user_settings import load_settings
from thalos_runtime.core.deps import get_engine
from thalos_runtime.plugins.chat_high_coherence_task import execution_defaults

router = APIRouter()

# Simple API key authentication (replace with proper auth in production)
ADMIN_API_KEY = os.getenv("THALOS_ADMIN_API_KEY", "admin-key-change-in-production")


def verify_admin_key(x_api_key: str | None = Header(None)) -> bool:
    """Verify admin API key."""
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return True


@router.get("/status", dependencies=[Depends(verify_admin_key)])
async def get_system_status() -> dict[str, Any]:
    """Get comprehensive system status.

    Requires admin API key.

    Returns:
        System status and metrics

    """
    try:
        # Get process info
        process = psutil.Process()

        # Memory info
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        # CPU info
        cpu_percent = process.cpu_percent(interval=0.1)

        # System info
        system_memory = psutil.virtual_memory()

        return {
            "status": "healthy",
            "version": __version__,
            "python_version": sys.version,
            "process": {
                "pid": process.pid,
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / 1024 / 1024,
                "memory_percent": memory_percent,
                "threads": process.num_threads(),
            },
            "system": {
                "total_memory_mb": system_memory.total / 1024 / 1024,
                "available_memory_mb": system_memory.available / 1024 / 1024,
                "memory_percent": system_memory.percent,
                "cpu_count": psutil.cpu_count(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {e!s}")


@router.get("/metrics", dependencies=[Depends(verify_admin_key)])
async def get_metrics() -> dict[str, Any]:
    """Get application metrics.

    Requires admin API key.

    Returns:
        Application metrics

    """
    # Import here to avoid circular dependency
    from thalos_runtime.plugins.chat_task import get_sessions
    sessions = get_sessions()
    from thalos_prime.api.routes.search import SEARCH_CACHE

    return {
        "sessions": {
            "total": len(sessions),
            "active": sum(1 for s in sessions.values()
                         if time.time() - s["last_activity"] < 3600),
        },
        "cache": {
            "search_entries": len(SEARCH_CACHE),
        },
        "timestamp": time.time(),
    }


@router.post("/cache/clear", dependencies=[Depends(verify_admin_key)])
async def clear_all_caches() -> dict[str, Any]:
    """Clear all application caches.

    Requires admin API key.

    Returns:
        Cache clear status

    """
    from thalos_prime.api.routes.search import SEARCH_CACHE

    search_count = len(SEARCH_CACHE)
    SEARCH_CACHE.clear()

    return {
        "message": "All caches cleared",
        "search_cache_entries": search_count,
    }


@router.post("/sessions/cleanup", dependencies=[Depends(verify_admin_key)])
async def cleanup_sessions(max_age_hours: int = 24) -> dict[str, Any]:
    """Clean up old sessions.

    Requires admin API key.

    Args:
        max_age_hours: Maximum session age in hours

    Returns:
        Cleanup status

    """
    from thalos_runtime.plugins.chat_task import get_sessions
    sessions = get_sessions()

    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    # Find and remove old sessions
    old_sessions = [
        sid for sid, session in sessions.items()
        if current_time - session["last_activity"] > max_age_seconds
    ]

    for sid in old_sessions:
        del sessions[sid]

    return {
        "message": "Session cleanup completed",
        "removed_sessions": len(old_sessions),
        "remaining_sessions": len(sessions),
    }


@router.get("/config", dependencies=[Depends(verify_admin_key)])
async def get_configuration() -> dict[str, Any]:
    """Get current configuration (non-sensitive).

    Requires admin API key.

    Returns:
        Configuration settings

    """
    from thalos_prime.api.config import config

    settings = load_settings()

    # Return non-sensitive config
    return {
        "host": config.host,
        "port": config.port,
        "desktop_host": settings.runtime.host,
        "desktop_port": settings.runtime.port,
        "desktop_log_level": settings.runtime.log_level,
        "cache_ttl": config.cache_ttl,
        "max_results_limit": config.max_results_limit,
        "enable_local_generation": config.enable_local_generation,
        "enable_remote_search": config.enable_remote_search,
        "llm_enabled": config.llm_enabled,
        "llm_provider": config.llm_provider if config.llm_enabled else None,
        "rate_limit_enabled": config.rate_limit_enabled,
    }


@router.get("/health/detailed", dependencies=[Depends(verify_admin_key)])
async def detailed_health_check() -> dict[str, Any]:
    """Detailed health check of all components.

    Requires admin API key.

    Returns:
        Detailed health status

    """
    health: dict[str, Any] = {
        "overall": "healthy",
        "components": {},
    }

    # Check generator
    try:
        from thalos_prime.lob_babel_generator import address_to_page
        test_page = address_to_page("test")
        health["components"]["generator"] = {
            "status": "healthy",
            "test_passed": len(test_page) == 3200,
        }
    except (ImportError, RuntimeError, ValueError, TypeError, AttributeError) as e:
        health["components"]["generator"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health["overall"] = "degraded"

    # Check enumerator
    try:
        from thalos_prime.lob_babel_enumerator import enumerate_addresses
        test_addrs = enumerate_addresses("test", max_results=1)
        health["components"]["enumerator"] = {
            "status": "healthy",
            "test_passed": len(test_addrs) > 0,
        }
    except (ImportError, RuntimeError, ValueError, TypeError, AttributeError) as e:
        health["components"]["enumerator"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health["overall"] = "degraded"

    # Check decoder
    try:
        from thalos_prime.lob_decoder import score_coherence
        test_score = score_coherence("test text")
        health["components"]["decoder"] = {
            "status": "healthy",
            "test_passed": hasattr(test_score, "overall_score"),
        }
    except (ImportError, RuntimeError, ValueError, TypeError, AttributeError) as e:
        health["components"]["decoder"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health["overall"] = "degraded"

    return health


@router.post("/shutdown", dependencies=[Depends(verify_admin_key)])
async def shutdown_server() -> dict[str, str]:
    """Initiate graceful server shutdown.

    Schedules a SIGTERM signal to be sent to the current process after the
    response has been delivered, allowing the ASGI lifespan cleanup to run.

    Requires admin API key.

    Returns:
        Shutdown confirmation message.

    """
    loop = asyncio.get_event_loop()
    loop.call_later(1.0, lambda: os.kill(os.getpid(), signal.SIGTERM))
    return {"message": "Shutdown initiated", "status": "terminating"}


@router.get("/tasks", dependencies=[Depends(verify_admin_key)])
@router.post("/tasks", dependencies=[Depends(verify_admin_key)])
async def list_runtime_tasks() -> dict[str, list[str]]:
    """Return registered runtime task names."""
    try:
        tasks = get_engine().task_names()
        return {"tasks": tasks}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/config/execution", dependencies=[Depends(verify_admin_key)])
async def get_execution_config() -> dict[str, float | int]:
    """Return execution defaults for high-coherence chat."""
    return execution_defaults()
