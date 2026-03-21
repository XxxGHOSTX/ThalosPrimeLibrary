"""Flask API for Babel subsystem.
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, Response, jsonify, request

from ..control.semantic_orchestrator import SemanticOrchestrator
from .protocol import RequestProtocol, ResponseProtocol


def create_app(storage_path: Path) -> Flask:
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

    def converse() -> Response:
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
        return jsonify(payload.model_dump())

    app.add_url_rule("/converse", view_func=converse, methods=["POST"])

    def checkpoint() -> Response:
        path = orchestrator.checkpoint()
        return jsonify({"checkpoint_path": str(path)})

    app.add_url_rule("/checkpoint", view_func=checkpoint, methods=["POST"])

    return app
