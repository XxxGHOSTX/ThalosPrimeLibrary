"""FastAPI application for Thalos Prime."""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from configs.config import get_settings
from src.control import ControlPlane
from src.data_plane.dialogue import DialogueManager
from src.observability import get_logger

# Initialize settings
settings = get_settings()

# Initialize logger
logger = get_logger(__name__)

# Global control plane and dialogue manager
control_plane: Optional[ControlPlane] = None
dialogue_manager: Optional[DialogueManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan."""
    global control_plane, dialogue_manager

    logger.info("Starting Thalos Prime")

    try:
        # Initialize control plane
        control_plane = ControlPlane(settings)
        control_plane.initialize()

        # Validate system
        if not control_plane.validate():
            logger.error("Validation failed - system may not function correctly")

        # Enter operating state
        control_plane.operate()

        # Initialize dialogue manager
        if control_plane.retriever and control_plane.state_store and control_plane.event_log:
            dialogue_manager = DialogueManager(
                retriever=control_plane.retriever,
                state_store=control_plane.state_store,
                event_log=control_plane.event_log,
                seed_salt=settings.seed_salt,
                time_bucket_seconds=settings.time_bucket_seconds,
                max_sentences=settings.max_sentences,
                top_k_retrieval=settings.top_k_retrieval,
            )
            logger.info("Dialogue manager initialized")
        else:
            logger.error("Failed to initialize dialogue manager")

        logger.info("Thalos Prime started successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Thalos Prime")

    if control_plane:
        control_plane.terminate()

    logger.info("Thalos Prime shut down")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Thalos Prime Library of Babel",
    description="Deterministic conversational system with TF-IDF retrieval",
    version="0.2.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# API key authentication (optional)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> None:
    """Verify API key if authentication is enabled."""
    if not settings.enable_api_key_auth:
        return

    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API key not configured")

    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


class ChatRequest(BaseModel):
    """Chat request model."""

    session_id: Optional[str] = Field(default=None, description="Session ID (auto-generated if not provided)")
    message: str = Field(..., description="User message", min_length=1)
    timestamp: Optional[float] = Field(default=None, description="Optional timestamp for seed generation")


class ChatResponse(BaseModel):
    """Chat response model."""

    session_id: str
    response: str
    seed: int
    retrieved_docs: int


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    """Serve the static UI."""
    ui_path = Path("static/index.html")

    if ui_path.exists():
        with open(ui_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())

    # Fallback inline UI
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Thalos Prime - Library of Babel</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <div class="container">
            <h1>Thalos Prime</h1>
            <h2>Library of Babel Conversational System</h2>
            <div id="chat-container">
                <div id="messages"></div>
            </div>
            <div class="input-container">
                <input type="text" id="message-input" placeholder="Enter your message..." />
                <button id="send-button">Send</button>
            </div>
            <div id="status"></div>
        </div>
        <script src="/static/js/app.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/static/css/style.css")
async def serve_css() -> FileResponse:
    """Serve CSS file."""
    css_path = Path("static/css/style.css")
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS not found")


@app.get("/static/js/app.js")
async def serve_js() -> FileResponse:
    """Serve JavaScript file."""
    js_path = Path("static/js/app.js")
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JavaScript not found")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, api_key: Optional[str] = Security(api_key_header)) -> ChatResponse:
    """
    Process a chat message and return a deterministic response.

    This endpoint:
    1. Generates a deterministic seed from session_id, message, salt, and time bucket
    2. Retrieves relevant documents using TF-IDF
    3. Generates a response using the seeded RNG
    4. Logs the seed and returns it in the response
    """
    await verify_api_key(api_key)

    if not dialogue_manager:
        raise HTTPException(status_code=503, detail="Dialogue manager not initialized")

    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Process message
        result = dialogue_manager.process_message(
            session_id=session_id,
            user_input=request.message,
            timestamp=request.timestamp,
        )

        return ChatResponse(
            session_id=session_id,
            response=result["response"],
            seed=result["seed"],
            retrieved_docs=result.get("retrieved_docs", 0),
        )

    except Exception as e:
        logger.error(f"Chat processing failed: {e}", session_id=session_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def status() -> Dict[str, Any]:
    """Get system status."""
    if not control_plane:
        return {"status": "not_initialized"}

    control_plane_state = control_plane.get_state()

    operating = False
    if isinstance(control_plane_state, dict):
        operating = bool(control_plane_state.get("operating"))

    if operating:
        status_value = "operational"
    elif isinstance(control_plane_state, dict) and "status" in control_plane_state:
        status_value = str(control_plane_state["status"])
    else:
        status_value = "not_operational"

    return {
        "status": status_value,
        "control_plane": control_plane_state,
        "dialogue_manager": dialogue_manager is not None,
    }


@app.post("/api/checkpoint")
async def create_checkpoint(api_key: Optional[str] = Security(api_key_header)) -> Dict[str, str]:
    """Create a system checkpoint."""
    await verify_api_key(api_key)

    if not control_plane:
        raise HTTPException(status_code=503, detail="Control plane not initialized")

    try:
        checkpoint_path = control_plane.checkpoint()
        return {"checkpoint_path": str(checkpoint_path)}
    except Exception as e:
        logger.error(f"Checkpoint creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reconcile")
async def reconcile(api_key: Optional[str] = Security(api_key_header)) -> Dict[str, bool]:
    """Trigger system reconciliation."""
    await verify_api_key(api_key)

    if not control_plane:
        raise HTTPException(status_code=503, detail="Control plane not initialized")

    try:
        success = control_plane.reconcile()
        return {"success": success}
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
