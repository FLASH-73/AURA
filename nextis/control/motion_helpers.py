"""Shared helpers for motion primitives.

Constants, joint-space conversion utilities, :class:`PrimitiveResult`, and
interpolation used by all primitive implementations in motion_primitives.py.

:class:`PrimitiveResult` lives here (rather than in primitives.py) to avoid
a circular import: primitives.py re-exports primitives from motion_primitives.py,
which in turn needs PrimitiveResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PrimitiveResult:
    """Result from executing a motion primitive.

    Attributes:
        success: Whether the primitive completed successfully.
        actual_force: Measured force at completion (Nm).
        actual_position: Joint positions at completion.
        duration_ms: Execution time in milliseconds.
        error_message: Description of failure, if any.
        force_history: Per-tick joint torques captured during execution.
            Each entry is a list of torques in JOINT_ORDER.
    """

    success: bool
    actual_force: float = 0.0
    actual_position: list[float] = field(default_factory=list)
    duration_ms: float = 0.0
    error_message: str | None = None
    force_history: list[list[float]] = field(default_factory=list)


# Canonical joint ordering matching MockRobot / Damiao arm layout
JOINT_ORDER: list[str] = [
    "base",
    "link1",
    "link2",
    "link3",
    "link4",
    "link5",
    "gripper",
]
JOINT_COUNT: int = len(JOINT_ORDER)

# Gripper position bounds (unitless, matches mock calibration range)
GRIPPER_CLOSED: float = 1.0
GRIPPER_OPEN: float = 0.0

# Control loop rate for primitives (Hz)
CONTROL_HZ: int = 60
CONTROL_DT: float = 1.0 / CONTROL_HZ


def obs_to_joints(obs: dict[str, float]) -> list[float]:
    """Extract joint positions from observation dict in JOINT_ORDER.

    Args:
        obs: Robot observation dict with ``{name}.pos`` keys.

    Returns:
        List of joint positions in canonical order.
    """
    return [obs.get(f"{name}.pos", 0.0) for name in JOINT_ORDER]


def joints_to_action(values: list[float]) -> dict[str, float]:
    """Build an action dict from a joint position list.

    Args:
        values: Joint positions in canonical order.

    Returns:
        Action dict with ``{name}.pos`` keys.
    """
    return {f"{name}.pos": val for name, val in zip(JOINT_ORDER, values, strict=False)}


def read_torques_list(robot: Any) -> list[float]:
    """Read joint torques from robot in canonical order.

    Args:
        robot: Connected robot instance with ``get_torques()``.

    Returns:
        List of torque values in JOINT_ORDER.
    """
    torques = robot.get_torques()
    return [torques.get(name, 0.0) for name in JOINT_ORDER]


def interpolate_step(
    current: list[float],
    target: list[float],
    alpha: float,
) -> list[float]:
    """Linearly interpolate each joint from *current* toward *target*.

    Args:
        current: Current joint positions.
        target: Target joint positions.
        alpha: Interpolation factor (0.0 = current, 1.0 = target).

    Returns:
        Interpolated joint positions.
    """
    alpha = max(0.0, min(1.0, alpha))
    return [c + alpha * (t - c) for c, t in zip(current, target, strict=False)]


def pad_target(target: list[float], current: list[float]) -> list[float]:
    """Pad a short target list with current positions to reach JOINT_COUNT.

    If *target* has fewer entries than JOINT_COUNT, remaining joints hold
    their current positions.

    Args:
        target: Target joint positions (may be shorter than JOINT_COUNT).
        current: Current joint positions (JOINT_COUNT entries).

    Returns:
        Padded target with exactly JOINT_COUNT entries.
    """
    if len(target) >= JOINT_COUNT:
        return target[:JOINT_COUNT]
    return target + current[len(target) :]


def position_reached(
    current: list[float],
    target: list[float],
    tolerance: float = 0.02,
) -> bool:
    """Check if all joints are within tolerance of target.

    Args:
        current: Current joint positions.
        target: Target joint positions.
        tolerance: Max per-joint error to consider "reached".

    Returns:
        True if every joint is within tolerance.
    """
    return all(abs(c - t) < tolerance for c, t in zip(current, target, strict=False))


def peak_abs_torque(torques: list[float]) -> float:
    """Return the maximum absolute torque from a reading.

    Args:
        torques: List of torque values.

    Returns:
        Maximum absolute value, or 0.0 if empty.
    """
    if not torques:
        return 0.0
    return max(abs(t) for t in torques)
