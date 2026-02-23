"""thalos_prime.agency — World Models and Active Inference module.

Exports:
    AgencyControlPlane      — Control Plane lifecycle orchestrator
    AgencyError             — typed exception
    WorldModel              — Data Plane world-model wrapper
    ActiveInferenceEngine   — Data Plane action-selection engine
    GoalEvaluator           — Data Plane goal evaluation
    PredictionEngine        — Data Plane prediction generation
    WorldState              — schema dataclass
    Goal                    — schema dataclass
    Action                  — schema dataclass
    Prediction              — schema dataclass
    GoalStatus              — StrEnum
"""

from thalos_prime.agency.active_inference import ActiveInferenceEngine
from thalos_prime.agency.control_plane import AgencyControlPlane, AgencyError
from thalos_prime.agency.goal_evaluator import GoalEvaluator
from thalos_prime.agency.prediction_engine import PredictionEngine
from thalos_prime.agency.schema import (
    Action,
    Goal,
    GoalStatus,
    Prediction,
    WorldState,
)
from thalos_prime.agency.world_model import WorldModel

__all__ = [
    "Action",
    "ActiveInferenceEngine",
    "AgencyControlPlane",
    "AgencyError",
    "Goal",
    "GoalEvaluator",
    "GoalStatus",
    "Prediction",
    "PredictionEngine",
    "WorldModel",
    "WorldState",
]
