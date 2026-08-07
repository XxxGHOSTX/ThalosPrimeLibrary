from thalos_prime.evolution import ModuleRegistry
from thalos_prime.evolution.observation import RuntimeRouter, SelfObserver


def test_observer_identifies_slowest_component():
    result = SelfObserver().analyze({
        "analysis": {"failure_rate": 0.1, "latency": 2.0, "efficiency": 0.8},
        "planning": {"failure_rate": 0.2, "latency": 5.0, "efficiency": 0.6},
    })
    assert result.slow_component == "planning"
    assert result.recommendation == "replace or optimize planning"


def test_runtime_router_uses_active_registry_version():
    registry = ModuleRegistry()
    registry.register(type("Spec", (), {"name": "x", "version": "v1", "handler": lambda x: x})())
    assert RuntimeRouter(registry).version("x") == "v1"
    assert RuntimeRouter(registry).select("x")(3) == 3
