"""Deterministic Epistemic VM for replayable verification workflows."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from thalos_prime.epistemic_v3.challenge import ChallengeEngine
from thalos_prime.epistemic_v3.claim_ir import ClaimCompiler, ClaimIR
from thalos_prime.epistemic_v3.lattice import BeliefLattice, BeliefPosition
from thalos_prime.epistemic_v3.warrant import Warrant


class Opcode(StrEnum):
    """Pure instructions supported by the baseline epistemic VM."""

    COMPILE_CLAIM = "COMPILE_CLAIM"
    BUILD_CHALLENGE_PLAN = "BUILD_CHALLENGE_PLAN"
    CLASSIFY_BELIEF = "CLASSIFY_BELIEF"
    EMIT_RESULT = "EMIT_RESULT"


class Instruction(BaseModel):
    """One immutable VM instruction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    opcode: Opcode
    args: Mapping[str, Any] = Field(default_factory=dict)


class EpistemicProgram(BaseModel):
    """Versioned program executed by the deterministic VM."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    program_id: str
    instructions: tuple[Instruction, ...]
    compiler_version: str = "epistemic-vm-v1"

    @classmethod
    def create(cls, instructions: tuple[Instruction, ...]) -> "EpistemicProgram":
        payload = [instruction.model_dump(mode="json") for instruction in instructions]
        program_id = "prog:" + hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(program_id=program_id, instructions=instructions)


class VMState(BaseModel):
    """Serializable machine state, suitable for replay and checkpointing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    instruction_pointer: int = 0
    registers: Mapping[str, Any] = Field(default_factory=dict)
    halted: bool = False


class VMResult(BaseModel):
    """Deterministic execution output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    program_id: str
    state: VMState
    claim: ClaimIR | None = None
    belief: BeliefPosition | None = None
    challenge_plan_id: str | None = None
    execution_fingerprint: str


class EpistemicVM:
    """Execute pure epistemic instructions without network or model calls."""

    VERSION = "epistemic-vm-v1"

    def execute(self, program: EpistemicProgram, inputs: Mapping[str, Any]) -> VMResult:
        registers: dict[str, Any] = dict(inputs)
        state = VMState(registers=registers)
        claim: ClaimIR | None = None
        belief: BeliefPosition | None = None
        challenge_plan_id: str | None = None
        ip = 0

        while ip < len(program.instructions):
            instruction = program.instructions[ip]
            if instruction.opcode is Opcode.COMPILE_CLAIM:
                result = ClaimCompiler.compile(
                    str(registers["query"]),
                    subject=instruction.args.get("subject"),
                    predicate=instruction.args.get("predicate"),
                    object=instruction.args.get("object"),
                    valid_from=instruction.args.get("valid_from"),
                    valid_to=instruction.args.get("valid_to"),
                )
                claim = result.claim
                registers["claim"] = claim
                registers["compiler_warnings"] = result.warnings
            elif instruction.opcode is Opcode.BUILD_CHALLENGE_PLAN:
                if claim is None:
                    raise RuntimeError("BUILD_CHALLENGE_PLAN requires a compiled claim")
                plan = ChallengeEngine.build_plan(claim)
                registers["challenge_plan"] = plan
                challenge_plan_id = plan.plan_id
            elif instruction.opcode is Opcode.CLASSIFY_BELIEF:
                if claim is None:
                    raise RuntimeError("CLASSIFY_BELIEF requires a compiled claim")
                warrant = registers.get("warrant")
                if not isinstance(warrant, Warrant):
                    raise TypeError("CLASSIFY_BELIEF requires a Warrant in VM inputs")
                lattice = BeliefLattice()
                belief = lattice.classify(
                    claim_id=claim.claim_id,
                    warrant=warrant,
                    challenge_count=int(registers.get("challenge_count", 0)),
                    resolved_challenge_count=int(registers.get("resolved_challenge_count", 0)),
                    failed_challenge_count=int(registers.get("failed_challenge_count", 0)),
                )
                registers["belief"] = belief
            elif instruction.opcode is Opcode.EMIT_RESULT:
                registers["result"] = {
                    "claim_id": claim.claim_id if claim else None,
                    "belief": belief.model_dump(mode="json") if belief else None,
                }
            else:
                raise RuntimeError(f"Unsupported opcode: {instruction.opcode}")
            ip += 1

        state = VMState(instruction_pointer=ip, registers=registers, halted=True)
        fingerprint_payload = {
            "program_id": program.program_id,
            "state": state.model_dump(mode="json"),
            "claim_id": claim.claim_id if claim else None,
            "belief": belief.model_dump(mode="json") if belief else None,
            "challenge_plan_id": challenge_plan_id,
        }
        execution_fingerprint = hashlib.sha256(
            json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return VMResult(
            program_id=program.program_id,
            state=state,
            claim=claim,
            belief=belief,
            challenge_plan_id=challenge_plan_id,
            execution_fingerprint=execution_fingerprint,
        )


DEFAULT_INVESTIGATION_PROGRAM = EpistemicProgram.create(
    (
        Instruction(opcode=Opcode.COMPILE_CLAIM),
        Instruction(opcode=Opcode.BUILD_CHALLENGE_PLAN),
        Instruction(opcode=Opcode.CLASSIFY_BELIEF),
        Instruction(opcode=Opcode.EMIT_RESULT),
    )
)
