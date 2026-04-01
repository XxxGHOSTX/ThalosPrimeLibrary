"""Thalos Prime - Six-stage Validation Pipeline subsystem.

Provides the deterministic, six-stage validation pipeline that gates
artifact candidates before admission to the belief base.  Each stage
is independently scoreable, and the aggregate verdict determines
whether an artifact is accepted, held pending, or rejected.
"""

from thalos_prime.validation.pipeline import (
    StageResult,
    ValidationPipeline,
    ValidationStage,
    ValidationVerdict,
)

__all__ = [
    "StageResult",
    "ValidationPipeline",
    "ValidationStage",
    "ValidationVerdict",
]
