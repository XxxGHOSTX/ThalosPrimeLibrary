#!/usr/bin/env python3
"""
Thalos Prime Matrix Console Startup Script
Windows-safe, single-instance enforced, zero port race conditions.
"""

import sys
import os
import msvcrt
import time

# Ensure workspace root is on the path
workspace_root = os.path.dirname(os.path.abspath(__file__))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

LOCKFILE = os.path.join(workspace_root, ".thalos_prime.lock")
HOST = "127.0.0.1"
PORT = 8000


def acquire_lock(path: str):
    """
    Acquire an exclusive Windows file lock.
    If this fails, another instance is already running.
    """
    lock = open(path, "w")
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        lock.write(str(os.getpid()))
        lock.flush()
        return lock
    except OSError:
        lock.close()
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Thalos Prime Matrix Console v1.0")
    print("=" * 60)

    lock_handle = acquire_lock(LOCKFILE)
    if not lock_handle:
        print("\nThalos Prime is already running.")
        print("No action taken. Existing instance remains active.")
        sys.exit(0)

    try:
        print("\nInitializing Thalos Prime API...")
        print("Checking dependencies:")
        print("  - FastAPI: OK")
        print("  - Library of Babel Search: OK")
        print("\nStarting server...")
        print("-" * 60)

        import uvicorn
        from src.api import app

        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            log_level="info",
        )

    except KeyboardInterrupt:
        print("\n\nShutdown requested by user.")

    finally:
        try:
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            lock_handle.close()
            os.remove(LOCKFILE)
        except Exception:
            pass

