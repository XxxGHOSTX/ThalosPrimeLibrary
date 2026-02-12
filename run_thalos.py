#!/usr/bin/env python3
"""
Thalos Prime Matrix Console Startup Script
Cross-platform, self-contained FastAPI app that fronts a structured
Library of Babel inspired search with a lightweight NLP/LLM-style stub.
"""

import hashlib
import os
import random
import sys
import time
from pathlib import Path
from typing import List, Optional

try:
    import msvcrt
except ImportError:  # Non-Windows platforms
    msvcrt = None

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

workspace_root = Path(__file__).resolve().parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

LOCKFILE = workspace_root / ".thalos_prime.lock"
HOST = "127.0.0.1"
PORT = 8000
LIBRARY_BASE = "https://libraryofbabel.info/book.cgi?hex="


def acquire_lock(path: Path):
    if msvcrt is None:
        return None
    lock = open(path, "w")
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        lock.write(str(os.getpid()))
        lock.flush()
        return lock
    except OSError:
        lock.close()
        return None


class SearchHit(BaseModel):
    url: str
    score: int
    snippet: str


class ChatRequest(BaseModel):
    message: str
    domain: Optional[str] = None
    constraints: Optional[List[str]] = None
    session_id: Optional[str] = None
    max_results: int = 2


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    hits: List[SearchHit]


def synthesize_hits(query: str, max_results: int, domain: Optional[str], constraints: Optional[List[str]]) -> List[SearchHit]:
    salt = "|".join(constraints) if constraints else ""
    basis = f"{domain or 'universal'}::{query}::{salt}"
    seed = int(hashlib.sha1(basis.encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed)
    hits: List[SearchHit] = []
    for _ in range(max(1, max_results)):
        hex_id = f"{rng.getrandbits(24):06x}"
        score = rng.randint(68, 97)
        snippet = (
            f"…{query[:42]}…" if len(query) > 42 else f"…{query}…"
        )
        hits.append(
            SearchHit(
                url=f"{LIBRARY_BASE}{hex_id}",
                score=score,
                snippet=f"{snippet} | domain={domain or 'universal'} | constraints={constraints or []} | coherence={score}/100 | variant=structured-mod",
            )
        )
    return hits


def build_reply(query: str, hits: List[SearchHit], domain: Optional[str], constraints: Optional[List[str]]) -> str:
    lines = ["BABEL_RESPONSE:", f"QUERY: {query}"]
    if domain:
        lines.append(f"DOMAIN: {domain}")
    if constraints:
        lines.append(f"CONSTRAINTS: {', '.join(constraints)}")
    for hit in hits:
        lines.append(f"- {hit.url} SCORE={hit.score}")
        lines.append(f"  {hit.snippet}")
    lines.append("COHERENCE: structured | ENGINE: LLM-stub | MODE: local")
    return "\n".join(lines)


app = FastAPI(title="Thalos Prime Matrix Console")


@app.get("/")
def serve_ui():
    return FileResponse(workspace_root / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "ts": time.time()}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    hits = synthesize_hits(payload.message, payload.max_results, payload.domain, payload.constraints)
    session_id = payload.session_id or hashlib.sha1(
        f"{payload.message}{time.time()}".encode("utf-8")
    ).hexdigest()[:16]
    reply = build_reply(payload.message, hits, payload.domain, payload.constraints)
    return ChatResponse(reply=reply, session_id=session_id, hits=hits)


@app.get("/api/search")
def search(query: str, max_results: int = 3):
    hits = synthesize_hits(query, max_results, domain=None, constraints=None)
    return JSONResponse({"query": query, "hits": [h.dict() for h in hits]})


if __name__ == "__main__":
    print("=" * 60)
    print("Thalos Prime Matrix Console")
    print("=" * 60)

    lock_handle = acquire_lock(LOCKFILE)
    try:
        print("\nStarting server on http://127.0.0.1:8000 ...")
        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
    finally:
        if lock_handle and msvcrt:
            try:
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                lock_handle.close()
                os.remove(LOCKFILE)
            except Exception:
                pass

