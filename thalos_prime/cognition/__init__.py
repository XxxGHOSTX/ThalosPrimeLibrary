"""Deterministic recursive-information cognition primitives.

This package operationalizes the information-first hypothesis as measurable
behavioral properties. It does not infer consciousness from behavior.
"""

from .models import CognitiveObservation, CognitiveScore, Prediction, SelfModelSnapshot
from .engine import RecursiveInformationEngine

__all__ = [
    "CognitiveObservation",
    "CognitiveScore",
    "Prediction",
    "SelfModelSnapshot",
    "RecursiveInformationEngine",
]
