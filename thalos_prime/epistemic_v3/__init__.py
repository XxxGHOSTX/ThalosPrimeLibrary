"""Thalos Prime epistemic computing layer v3.

This package introduces the Claim IR, Witness Calculus, Warrant Algebra,
challenge/falsification engine, belief lattice, decision compiler,
epistemic VM, perturbation stability analysis, counterfactual decision
analysis, and immutable epistemic transactions. It sits above the
transactional foundation without coupling epistemic computation to MCP or
any model provider.
"""

from thalos_prime.epistemic_v3.challenge import ChallengeEngine, ChallengePlan
from thalos_prime.epistemic_v3.claim_ir import ClaimCompiler, ClaimIR
from thalos_prime.epistemic_v3.counterfactual import CounterfactualEngine, CounterfactualReport
from thalos_prime.epistemic_v3.decision import DecisionArtifact, DecisionCompiler, DecisionReason
from thalos_prime.epistemic_v3.lattice import BeliefLattice, BeliefPosition
from thalos_prime.epistemic_v3.stability import StabilityAnalyzer, StabilityReport
from thalos_prime.epistemic_v3.transaction import EpistemicTransaction
from thalos_prime.epistemic_v3.vm import EpistemicProgram, EpistemicVM
from thalos_prime.epistemic_v3.warrant import Warrant, WarrantAlgebra
from thalos_prime.epistemic_v3.witness import Witness, WitnessCalculus

__all__ = [
    "BeliefLattice",
    "BeliefPosition",
    "ChallengeEngine",
    "ChallengePlan",
    "ClaimCompiler",
    "ClaimIR",
    "CounterfactualEngine",
    "CounterfactualReport",
    "DecisionArtifact",
    "DecisionCompiler",
    "DecisionReason",
    "EpistemicProgram",
    "EpistemicTransaction",
    "EpistemicVM",
    "StabilityAnalyzer",
    "StabilityReport",
    "Warrant",
    "WarrantAlgebra",
    "Witness",
    "WitnessCalculus",
]
