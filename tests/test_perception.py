"""Perception verification tests — checkers, verifier dispatch, and mock data.

17 tests covering all four checker types with pass/fail scenarios, the
StepVerifier dispatcher, and MockRobot.generate_execution_data for each
criteria type.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from nextis.assembly.models import AssemblyStep, SuccessCriteria
from nextis.hardware.mock import MockRobot
from nextis.perception.checks import (
    check_classifier,
    check_force_signature,
    check_force_threshold,
    check_position,
)
from nextis.perception.types import ExecutionData
from nextis.perception.verifier import StepVerifier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_step(
    criteria_type: str = "position",
    threshold: float | None = None,
    pattern: str | None = None,
    model: str | None = None,
    primitive_params: dict | None = None,
) -> AssemblyStep:
    """Create a minimal AssemblyStep with the given success criteria."""
    return AssemblyStep(
        id="test_step",
        name="Test step",
        part_ids=[],
        dependencies=[],
        handler="primitive",
        success_criteria=SuccessCriteria(
            type=criteria_type,
            threshold=threshold,
            pattern=pattern,
            model=model,
        ),
        primitive_params=primitive_params,
    )


# ---------------------------------------------------------------------------
# 1. Position checker
# ---------------------------------------------------------------------------


def test_check_position_pass() -> None:
    """Position within tolerance passes."""
    step = _make_step(
        criteria_type="position",
        primitive_params={"target_pose": [100.0, 200.0, 300.0, 0.0, 0.0, 0.0]},
    )
    data = ExecutionData(final_position=[100.5, 200.3, 300.1])
    result = check_position(step, data)

    assert result.passed is True
    assert result.measured_value is not None
    assert result.measured_value < 2.0


def test_check_position_fail() -> None:
    """Position 5 mm off target fails."""
    step = _make_step(
        criteria_type="position",
        primitive_params={"target_pose": [100.0, 200.0, 300.0, 0.0, 0.0, 0.0]},
    )
    data = ExecutionData(final_position=[105.0, 200.0, 300.0])
    result = check_position(step, data)

    assert result.passed is False
    assert result.measured_value is not None
    assert result.measured_value == pytest.approx(5.0, abs=0.01)


def test_check_position_no_target() -> None:
    """No target_pose in params skips with low confidence."""
    step = _make_step(criteria_type="position", primitive_params={})
    data = ExecutionData(final_position=[1.0, 2.0, 3.0])
    result = check_position(step, data)

    assert result.passed is True
    assert result.confidence == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# 2. Force threshold checker
# ---------------------------------------------------------------------------


def test_check_force_threshold_pass() -> None:
    """Peak force above threshold passes."""
    step = _make_step(criteria_type="force_threshold", threshold=10.0)
    data = ExecutionData(peak_force=12.0)
    result = check_force_threshold(step, data)

    assert result.passed is True
    assert result.measured_value == pytest.approx(12.0)


def test_check_force_threshold_fail() -> None:
    """Peak force below threshold fails."""
    step = _make_step(criteria_type="force_threshold", threshold=10.0)
    data = ExecutionData(peak_force=8.0)
    result = check_force_threshold(step, data)

    assert result.passed is False


def test_check_force_threshold_no_threshold() -> None:
    """No threshold defined skips with low confidence."""
    step = _make_step(criteria_type="force_threshold", threshold=None)
    data = ExecutionData(peak_force=5.0)
    result = check_force_threshold(step, data)

    assert result.passed is True
    assert result.confidence == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# 3a. Force signature — snap fit
# ---------------------------------------------------------------------------


def test_check_snap_fit_pass() -> None:
    """Snap-fit with clear peak + drop passes."""
    ramp = list(np.linspace(0.5, 5.0, 16))
    drop = [2.0, 1.5, 1.2, 1.1]
    hold = [1.0] * 10
    force_history = ramp + drop + hold

    step = _make_step(criteria_type="force_signature", pattern="snap_fit")
    data = ExecutionData(force_history=force_history)
    result = check_force_signature(step, data)

    assert result.passed is True


def test_check_snap_fit_fail() -> None:
    """Flat noise fails snap-fit detection."""
    force_history = [0.02] * 30

    step = _make_step(criteria_type="force_signature", pattern="snap_fit")
    data = ExecutionData(force_history=force_history)
    result = check_force_signature(step, data)

    assert result.passed is False


# ---------------------------------------------------------------------------
# 3b. Force signature — meshing
# ---------------------------------------------------------------------------


def test_check_meshing_pass() -> None:
    """Oscillating force with 4+ peaks passes meshing."""
    force_history = [1.5 + 1.2 * math.sin(i * math.pi / 4) for i in range(40)]

    step = _make_step(criteria_type="force_signature", pattern="meshing")
    data = ExecutionData(force_history=force_history)
    result = check_force_signature(step, data)

    assert result.passed is True
    assert result.measured_value is not None
    assert result.measured_value >= 3.0


def test_check_meshing_fail() -> None:
    """Monotonic force fails meshing detection."""
    force_history = list(np.linspace(0.1, 2.0, 30))

    step = _make_step(criteria_type="force_signature", pattern="meshing")
    data = ExecutionData(force_history=force_history)
    result = check_force_signature(step, data)

    assert result.passed is False


# ---------------------------------------------------------------------------
# 3c. Force signature — press fit
# ---------------------------------------------------------------------------


def test_check_press_fit_pass() -> None:
    """Monotonic rise to target passes press-fit."""
    force_history = list(np.linspace(0.5, 12.0, 30))

    step = _make_step(criteria_type="force_signature", pattern="press_fit", threshold=10.0)
    data = ExecutionData(force_history=force_history)
    result = check_force_signature(step, data)

    assert result.passed is True


def test_check_press_fit_fail() -> None:
    """Plateau below target fails press-fit."""
    ramp = list(np.linspace(0.2, 4.0, 10))
    plateau = [4.0 + 0.1 * (i % 2) for i in range(10)]
    force_history = ramp + plateau

    step = _make_step(criteria_type="force_signature", pattern="press_fit", threshold=10.0)
    data = ExecutionData(force_history=force_history)
    result = check_force_signature(step, data)

    assert result.passed is False


# ---------------------------------------------------------------------------
# 4. Classifier checker
# ---------------------------------------------------------------------------


def test_check_classifier_no_model() -> None:
    """No model path skips with confidence 0.5."""
    step = _make_step(criteria_type="classifier", model=None)
    data = ExecutionData()
    result = check_classifier(step, data)

    assert result.passed is True
    assert result.confidence == pytest.approx(0.5)


def test_check_classifier_no_camera(tmp_path: object) -> None:
    """Model exists but no camera frame fails."""
    from pathlib import Path

    model_file = Path(str(tmp_path)) / "fake_model.pt"
    model_file.write_bytes(b"fake")

    step = _make_step(criteria_type="classifier", model=str(model_file))
    data = ExecutionData(camera_frame=None)
    result = check_classifier(step, data)

    assert result.passed is False
    assert result.confidence == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# 5. StepVerifier dispatch
# ---------------------------------------------------------------------------


async def test_verifier_dispatches_correctly() -> None:
    """Verifier routes to check_position and returns a pass."""
    step = _make_step(
        criteria_type="position",
        primitive_params={"target_pose": [10.0, 20.0, 30.0, 0, 0, 0]},
    )
    data = ExecutionData(final_position=[10.0, 20.0, 30.0])
    verifier = StepVerifier()
    result = await verifier.verify(step, data)

    assert result.passed is True


async def test_verifier_unknown_type() -> None:
    """Unknown criteria type returns pass with confidence 0.5."""
    step = _make_step(criteria_type="unknown_xyz")
    data = ExecutionData()
    verifier = StepVerifier()
    result = await verifier.verify(step, data)

    assert result.passed is True
    assert result.confidence == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 6. MockRobot.generate_execution_data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "criteria_type,pattern,threshold,checker",
    [
        ("force_threshold", None, 5.0, check_force_threshold),
        ("position", None, None, check_position),
        ("force_signature", "snap_fit", None, check_force_signature),
        ("force_signature", "meshing", None, check_force_signature),
        ("force_signature", "press_fit", 5.0, check_force_signature),
    ],
    ids=["force_threshold", "position", "snap_fit", "meshing", "press_fit"],
)
def test_mock_execution_data(
    criteria_type: str,
    pattern: str | None,
    threshold: float | None,
    checker: object,
) -> None:
    """MockRobot generates data that passes the corresponding checker."""
    step = _make_step(
        criteria_type=criteria_type,
        threshold=threshold,
        pattern=pattern,
        primitive_params={"target_pose": [10.0, 20.0, 30.0, 0.0, 0.0, 0.0]},
    )
    mock = MockRobot()
    exec_data = mock.generate_execution_data(step, force_success=True)

    assert exec_data.duration_ms > 0
    assert isinstance(exec_data.force_history, list)

    # Feed through the checker — must pass
    result = checker(step, exec_data)  # type: ignore[operator]
    assert result.passed is True, f"Checker failed: {result.detail}"
