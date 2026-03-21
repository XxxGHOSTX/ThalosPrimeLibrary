"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.

⚠️  EXPERIMENTAL TEST STUB — NOT STABLE
"""

import pytest
from experimental.experiment_template.experiment import ExperimentStub


def test_experiment_requires_valid_seed() -> None:
    """Verify that an invalid seed raises ValueError."""
    with pytest.raises(ValueError):
        ExperimentStub(seed=0)


def test_experiment_run_returns_dict() -> None:
    """Verify that run() returns a dict with the expected keys."""
    exp = ExperimentStub(seed=9876543210123456)
    result = exp.run({"input": "test"})
    assert isinstance(result, dict)
    assert result["is_experimental"] is True
    assert result["seed"] == 9876543210123456
