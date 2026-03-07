"""Flask API for Babel subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Flask, Response, jsonify, request

from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator

from .protocol import RequestProtocol, ResponseProtocol

if TYPE_CHECKING:
    from pathlib import Path


def create_app(storage_path: Path) -> Flask:
    """Create and configure the Flask application with all Babel routes."""
    orchestrator = SemanticOrchestrator(storage_path)
    orchestrator.initialize()
    app = Flask(__name__)

    def health() -> tuple[Response, int]:
        status = orchestrator.get_status()
        return (
            jsonify(
                {
                    "status": "healthy",
                    "phase": status.phase.name,
                    "conversations": status.conversations_handled,
                }
            ),
            200,
        )

    app.add_url_rule("/health", view_func=health, methods=["GET"])

    @app.post("/converse")
    def converse() -> tuple[Response, int]:  # pyright: ignore[reportUnusedFunction]
        """Handle a converse request and return a semantic response."""
        data = request.get_json(force=True)
        req = RequestProtocol(**data)
        response = orchestrator.handle_semantic_input(req.user_input, req.session_id)
        payload = ResponseProtocol(
            text=response.text,
            coordinate=response.coordinate.as_string(),
            template_id=response.template_used,
            semantic_preserved=response.semantic_preserved,
            coherent=response.coherence_report.is_coherent,
            metadata={
                "frame_type": response.frame.frame_type.name,
                "variation_degree": response.variation_degree,
            },
        )
        return jsonify(payload.model_dump()), 200

    @app.post("/checkpoint")
    def checkpoint() -> tuple[Response, int]:  # pyright: ignore[reportUnusedFunction]
        """Trigger an orchestrator checkpoint and return the checkpoint path."""
        path = orchestrator.checkpoint()
        return jsonify({"checkpoint_path": str(path)}), 200

    return app
