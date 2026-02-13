"""
Admin Routes - Administrative endpoints

Provides administrative and monitoring functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
import time
import sys
import psutil
import os

from thalos_prime import __version__

router = APIRouter()

# Simple API key authentication (replace with proper auth in production)
ADMIN_API_KEY = os.getenv("THALOS_ADMIN_API_KEY", "admin-key-change-in-production")


def verify_admin_key(x_api_key: str = Header(None)):
    """Verify admin API key"""
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return True


@router.get("/status", dependencies=[Depends(verify_admin_key)])
async def get_system_status():
    """
    Get comprehensive system status.
    
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
            'status': 'healthy',
            'version': __version__,
            'python_version': sys.version,
            'process': {
                'pid': process.pid,
                'cpu_percent': cpu_percent,
                'memory_mb': memory_info.rss / 1024 / 1024,
                'memory_percent': memory_percent,
                'threads': process.num_threads()
            },
            'system': {
                'total_memory_mb': system_memory.total / 1024 / 1024,
                'available_memory_mb': system_memory.available / 1024 / 1024,
                'memory_percent': system_memory.percent,
                'cpu_count': psutil.cpu_count()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/metrics", dependencies=[Depends(verify_admin_key)])
async def get_metrics():
    """
    Get application metrics.
    
    Requires admin API key.
    
    Returns:
        Application metrics
    """
    # Import here to avoid circular dependency
    from thalos_prime.api.routes.chat import SESSIONS
    from thalos_prime.api.routes.search import SEARCH_CACHE
    
    return {
        'sessions': {
            'total': len(SESSIONS),
            'active': sum(1 for s in SESSIONS.values() 
                         if time.time() - s['last_activity'] < 3600)
        },
        'cache': {
            'search_entries': len(SEARCH_CACHE)
        },
        'timestamp': time.time()
    }


@router.post("/cache/clear", dependencies=[Depends(verify_admin_key)])
async def clear_all_caches():
    """
    Clear all application caches.
    
    Requires admin API key.
    
    Returns:
        Cache clear status
    """
    from thalos_prime.api.routes.search import SEARCH_CACHE
    
    search_count = len(SEARCH_CACHE)
    SEARCH_CACHE.clear()
    
    return {
        'message': 'All caches cleared',
        'search_cache_entries': search_count
    }


@router.post("/sessions/cleanup", dependencies=[Depends(verify_admin_key)])
async def cleanup_sessions(max_age_hours: int = 24):
    """
    Clean up old sessions.
    
    Requires admin API key.
    
    Args:
        max_age_hours: Maximum session age in hours
    
    Returns:
        Cleanup status
    """
    from thalos_prime.api.routes.chat import SESSIONS
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    # Find and remove old sessions
    old_sessions = [
        sid for sid, session in SESSIONS.items()
        if current_time - session['last_activity'] > max_age_seconds
    ]
    
    for sid in old_sessions:
        del SESSIONS[sid]
    
    return {
        'message': 'Session cleanup completed',
        'removed_sessions': len(old_sessions),
        'remaining_sessions': len(SESSIONS)
    }


@router.get("/config", dependencies=[Depends(verify_admin_key)])
async def get_configuration():
    """
    Get current configuration (non-sensitive).
    
    Requires admin API key.
    
    Returns:
        Configuration settings
    """
    from thalos_prime.api.config import config
    
    # Return non-sensitive config
    return {
        'host': config.host,
        'port': config.port,
        'cache_ttl': config.cache_ttl,
        'max_results_limit': config.max_results_limit,
        'enable_local_generation': config.enable_local_generation,
        'enable_remote_search': config.enable_remote_search,
        'llm_enabled': config.llm_enabled,
        'llm_provider': config.llm_provider if config.llm_enabled else None,
        'rate_limit_enabled': config.rate_limit_enabled
    }


@router.get("/health/detailed", dependencies=[Depends(verify_admin_key)])
async def detailed_health_check():
    """
    Detailed health check of all components.
    
    Requires admin API key.
    
    Returns:
        Detailed health status
    """
    health = {
        'overall': 'healthy',
        'components': {}
    }
    
    # Check generator
    try:
        from thalos_prime.lob_babel_generator import address_to_page
        test_page = address_to_page("test")
        health['components']['generator'] = {
            'status': 'healthy',
            'test_passed': len(test_page) == 3200
        }
    except Exception as e:
        health['components']['generator'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health['overall'] = 'degraded'
    
    # Check enumerator
    try:
        from thalos_prime.lob_babel_enumerator import enumerate_addresses
        test_addrs = enumerate_addresses("test", max_results=1)
        health['components']['enumerator'] = {
            'status': 'healthy',
            'test_passed': len(test_addrs) > 0
        }
    except Exception as e:
        health['components']['enumerator'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health['overall'] = 'degraded'
    
    # Check decoder
    try:
        from thalos_prime.lob_decoder import score_coherence
        test_score = score_coherence("test text")
        health['components']['decoder'] = {
            'status': 'healthy',
            'test_passed': hasattr(test_score, 'overall_score')
        }
    except Exception as e:
        health['components']['decoder'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health['overall'] = 'degraded'
    
    return health


@router.post("/shutdown", dependencies=[Depends(verify_admin_key)])
async def shutdown_server():
    """
    Initiate graceful server shutdown.
    
    Requires admin API key.
    
    WARNING: This will stop the server!
    
    Returns:
        Shutdown confirmation
    """
    # In production, this would trigger a graceful shutdown
    # For now, just return a message
    return {
        'message': 'Shutdown command received',
        'warning': 'Shutdown not implemented in this version'
    }
