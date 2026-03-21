"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

import sys
import argparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .session_manager import ThalosSessionManager
from core.utilities import validate_seed

app = FastAPI(
    title="Thalos Prime Control Plane",
    version="2.0.0",
    description="© 2026 Tony Ray Macier III. Sovereign deterministic control plane.",
)

_session_manager = ThalosSessionManager()


class SessionRequest(BaseModel):
    """Request body for creating a new session."""

    context: dict = {}


class TurnRequest(BaseModel):
    """Request body for adding a conversation turn."""

    role: str
    content: str


@app.get("/health")
def health() -> dict:
    """Liveness probe — returns service status."""
    return {
        "status": "ok",
        "service": "thalos-control-plane",
        "version": "2.0.0",
        "owner": "Tony Ray Macier III",
    }


@app.post("/sessions", status_code=201)
def create_session(request: SessionRequest) -> dict:
    """Create a new session and derive its deterministic execution seed."""
    session_id = _session_manager.create_session(context=request.context)
    session = _session_manager.get_session(session_id)
    return {"session_id": session_id, "seed": session["seed"]}


@app.post("/sessions/{session_id}/turns")
def add_turn(session_id: str, request: TurnRequest) -> dict:
    """Append a conversation turn to an existing session."""
    try:
        state_hash = _session_manager.add_turn(session_id, request.role, request.content)
        return {"state_hash": state_hash, "session_id": session_id}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@app.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    """Retrieve the full session state including all turns."""
    session = _session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


def main() -> None:
    """CLI entry point for the control plane API server."""
    parser = argparse.ArgumentParser(description="Thalos Prime Control Plane API")
    parser.add_argument("--seed", type=int, required=True, help="64-bit execution seed (required)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    try:
        validate_seed(args.seed)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
