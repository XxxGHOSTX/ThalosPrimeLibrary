"""Tests for the capability amplification kernel."""

from __future__ import annotations

from thalos_runtime.core.capability_amplification import (
    AmplificationStatus,
    Capability,
    CapabilityAmplifier,
    CapabilityRouter,
    CallableCapabilityProvider,
    CallableValidator,
    FailureCode,
    TaskContract,
    ValidationCheck,
)


def _provider(provider_id: str, value: object) -> CallableCapabilityProvider:
    return CallableCapabilityProvider(
        provider_id=provider_id,
        capabilities=frozenset({Capability.RETRIEVE}),
        operation=lambda _payload, result=value: result,
    )


def _non_empty_requirement() -> CallableValidator:
    def check(_contract: TaskContract, output: object) -> ValidationCheck:
        return ValidationCheck(
            validator="test.non_empty",
            passed=bool(output),
            blocking=True,
            detail="output truthiness",
        )

    return CallableValidator("test.non_empty", check)


def test_router_is_deterministic() -> None:
    router = CapabilityRouter()
    router.register(_provider("z-provider", "z"))
    router.register(_provider("a-provider", "a"))

    assert [p.provider_id for p in router.candidates(frozenset({Capability.RETRIEVE}))] == [
        "a-provider",
        "z-provider",
    ]


def test_verified_result_stops_after_first_valid_provider() -> None:
    router = CapabilityRouter()
    calls: list[str] = []
    router.register(
        CallableCapabilityProvider(
            provider_id="first",
            capabilities=frozenset({Capability.RETRIEVE}),
            operation=lambda _payload: calls.append("first") or "usable",
        )
    )
    router.register(
        CallableCapabilityProvider(
            provider_id="second",
            capabilities=frozenset({Capability.RETRIEVE}),
            operation=lambda _payload: calls.append("second") or "fallback",
        )
    )
    amplifier = CapabilityAmplifier(router, validators=(_non_empty_requirement(),))
    contract = amplifier.build_contract(
        objective="retrieve data",
        payload={"query": "x"},
        required_capabilities=(Capability.RETRIEVE,),
        acceptance_criteria=("non_empty",),
    )

    result = amplifier.run(contract)

    assert result.status is AmplificationStatus.COMPLETED_VERIFIED
    assert result.provider_id == "first"
    assert result.attempts[0].attempt == 1
    assert calls == ["first"]


def test_failover_requires_a_different_provider() -> None:
    router = CapabilityRouter()
    calls: list[str] = []
    router.register(
        CallableCapabilityProvider(
            provider_id="first",
            capabilities=frozenset({Capability.RETRIEVE}),
            operation=lambda _payload: calls.append("first") or "",
        )
    )
    router.register(
        CallableCapabilityProvider(
            provider_id="second",
            capabilities=frozenset({Capability.RETRIEVE}),
            operation=lambda _payload: calls.append("second") or "valid",
        )
    )
    amplifier = CapabilityAmplifier(router, validators=(_non_empty_requirement(),))
    contract = amplifier.build_contract(
        objective="retrieve data",
        payload={"query": "x"},
        required_capabilities=(Capability.RETRIEVE,),
        acceptance_criteria=("non_empty",),
        max_attempts=2,
    )

    result = amplifier.run(contract)

    assert result.status is AmplificationStatus.COMPLETED_VERIFIED
    assert result.provider_id == "second"
    assert calls == ["first", "second"]
    assert FailureCode.VALIDATION_FAILED in result.failures


def test_missing_capability_is_blocked() -> None:
    router = CapabilityRouter()
    amplifier = CapabilityAmplifier(router)
    contract = amplifier.build_contract(
        objective="calculate",
        payload={"expression": "2+2"},
        required_capabilities=(Capability.CALCULATE,),
        acceptance_criteria=("deterministic_result",),
    )

    result = amplifier.run(contract)

    assert result.status is AmplificationStatus.BLOCKED
    assert result.failures == (FailureCode.CAPABILITY_UNAVAILABLE,)


def test_contract_id_is_reproducible() -> None:
    router = CapabilityRouter()
    amplifier = CapabilityAmplifier(router)
    first = amplifier.build_contract(
        objective="retrieve data",
        payload={"query": "x"},
        required_capabilities=(Capability.RETRIEVE,),
        acceptance_criteria=("non_empty",),
    )
    second = amplifier.build_contract(
        objective="retrieve data",
        payload={"query": "x"},
        required_capabilities=(Capability.RETRIEVE,),
        acceptance_criteria=("non_empty",),
    )
    assert first.task_id == second.task_id
