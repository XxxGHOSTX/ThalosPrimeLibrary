"""Thalos Prime epistemic computing layer v3.

This package introduces the Claim IR, Witness Calculus, Warrant Algebra,
challenge/falsification engine, belief lattice, epistemic VM, and perturbation
stability analysis. It is designed to sit above the existing transactional
foundation without coupling the epistemic model to MCP or any model provider.
"""

from thalos_prime.epistemic_v3.claim_ir import ClaimIR, ClaimCompiler
from thalos_prime.epistemic_v3.witness import Witness, WitnessCalculus
from thalos_prime.epistemic_v3.warrant import Warrant, WarrantAlgebra
from thalos_prime.epistemic_v3.challenge import ChallengePlan, ChallengeEngine
from thalos_prime.epistemic_v3.lattice import BeliefPosition, BeliefLattice
from thalos_prime.epistemic_v3.vm import EpistemicProgram, EpistemicVM
from thalos_prime.epistemic_v3.stability import StabilityReport, StabilityAnalyzer

__all__ = [
    "BeliefLattice",
    "BeliefPosition",
    "ChallengeEngine",
    "ChallengePlan",
    "ClaimCompiler",
    "ClaimIR",
    "EpistemicProgram",
    "EpistemicVM",
    "StabilityAnalyzer",
    "StabilityReport",
    "Warrant",
    "WarrantAlgebra",
    "Witness",
    "WitnessCalculus",
]
