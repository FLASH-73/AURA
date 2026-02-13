"""Unit tests for real motion primitive implementations.

Tests both the mock path (robot=None) and real path (MockRobot) to verify
that primitives produce correct results and force history data.
"""

from __future__ import annotations

from nextis.control.motion_primitives import (
    guarded_move,
    linear_insert,
    move_to,
    pick,
    place,
    press_fit,
    screw,
)
from nextis.control.primitives import PrimitiveLibrary
from nextis.hardware.mock import MockRobot


class ControlledMockRobot(MockRobot):
    """MockRobot with configurable torque returns for force-threshold tests."""

    def __init__(self, torque: float = 0.5) -> None:
        super().__init__()
        self._fixed_torque = torque

    def get_torques(self) -> dict[str, float]:
        """Return fixed torques for predictable test behavior."""
        from nextis.hardware.mock import MOCK_JOINT_NAMES

        return {n: self._fixed_torque for n in MOCK_JOINT_NAMES}


# ------------------------------------------------------------------
# Mock path (robot=None) — backward compat with existing stubs
# ------------------------------------------------------------------


async def test_move_to_mock_path() -> None:
    """move_to with robot=None sleeps and returns success."""
    result = await move_to(None, target_pose=[1, 2, 3], timeout=0.1, _speed_factor=0.01)
    assert result.success
    assert result.force_history == []
    assert result.actual_position == [1, 2, 3]


async def test_pick_mock_path() -> None:
    """pick with robot=None returns success with expected force."""
    result = await pick(
        None, grasp_pose=[0, 0, 0], force_threshold=0.5, timeout=0.1, _speed_factor=0.01
    )
    assert result.success
    assert result.actual_force == 0.5
    assert result.force_history == []


async def test_place_mock_path() -> None:
    """place with robot=None returns success."""
    result = await place(None, target_pose=[1, 2, 3], timeout=0.1, _speed_factor=0.01)
    assert result.success
    assert result.force_history == []


async def test_guarded_move_mock_path() -> None:
    """guarded_move with robot=None returns contact force."""
    result = await guarded_move(
        None, direction=[0, 0, -1], force_threshold=5.0, timeout=0.1, _speed_factor=0.01
    )
    assert result.success
    assert result.actual_force == 5.0


async def test_linear_insert_mock_path() -> None:
    """linear_insert with robot=None returns 60% of force limit."""
    result = await linear_insert(
        None, target_pose=[0], force_limit=10.0, timeout=0.1, _speed_factor=0.01
    )
    assert result.success
    assert abs(result.actual_force - 6.0) < 0.01


async def test_screw_mock_path() -> None:
    """screw with robot=None returns 80% of torque limit."""
    result = await screw(None, torque_limit=2.0, timeout=0.1, _speed_factor=0.01)
    assert result.success
    assert abs(result.actual_force - 1.6) < 0.01


async def test_press_fit_mock_path() -> None:
    """press_fit with robot=None returns target force."""
    result = await press_fit(None, force_target=15.0, timeout=0.1, _speed_factor=0.01)
    assert result.success
    assert result.actual_force == 15.0


# ------------------------------------------------------------------
# Real path (MockRobot) — control loop + force history
# ------------------------------------------------------------------


async def test_move_to_with_mock_robot() -> None:
    """move_to with MockRobot converges and returns force history."""
    robot = MockRobot()
    target = [0.0] * 7
    result = await move_to(robot, target_pose=target, velocity=0.8, timeout=3.0)
    assert result.success
    assert result.duration_ms > 0
    assert len(result.force_history) > 0
    assert len(result.actual_position) == 7


async def test_pick_with_controlled_robot() -> None:
    """pick with ControlledMockRobot detects gripper force."""
    robot = ControlledMockRobot(torque=0.8)
    result = await pick(robot, grasp_pose=[0.0] * 7, force_threshold=0.5, timeout=5.0)
    assert result.success
    assert result.actual_force >= 0.5
    assert len(result.force_history) > 0


async def test_place_with_controlled_robot() -> None:
    """place with ControlledMockRobot opens gripper (low torque = release confirmed)."""
    robot = ControlledMockRobot(torque=0.05)
    result = await place(robot, target_pose=[0.0] * 7, release_force=0.2, timeout=5.0)
    assert result.success
    assert len(result.force_history) > 0


async def test_guarded_move_with_controlled_robot() -> None:
    """guarded_move with high-torque mock detects contact."""
    robot = ControlledMockRobot(torque=6.0)
    result = await guarded_move(robot, direction=[0, 0, -1], force_threshold=5.0, timeout=3.0)
    assert result.success
    assert result.actual_force >= 5.0
    assert len(result.force_history) > 0


async def test_linear_insert_with_controlled_robot() -> None:
    """linear_insert with high-torque mock triggers force limit (seating)."""
    robot = ControlledMockRobot(torque=12.0)
    result = await linear_insert(robot, target_pose=[0.0] * 7, force_limit=10.0, timeout=3.0)
    assert result.success
    assert result.actual_force >= 10.0
    assert len(result.force_history) > 0


async def test_screw_with_controlled_robot() -> None:
    """screw with high-torque mock triggers torque limit."""
    robot = ControlledMockRobot(torque=3.0)
    result = await screw(robot, torque_limit=2.0, timeout=3.0)
    assert result.success
    assert result.actual_force >= 2.0
    assert len(result.force_history) > 0


async def test_press_fit_with_controlled_robot() -> None:
    """press_fit with high-torque mock reaches target force."""
    robot = ControlledMockRobot(torque=20.0)
    result = await press_fit(robot, force_target=15.0, timeout=3.0)
    assert result.success
    assert result.actual_force >= 15.0
    assert len(result.force_history) > 0


async def test_move_to_timeout() -> None:
    """move_to times out if target is unreachable (robot doesn't move on its own)."""
    robot = MockRobot()
    # Set a target far from where sine-wave initial observation will be
    result = await move_to(robot, target_pose=[10.0] * 7, velocity=0.001, timeout=0.1)
    assert not result.success
    assert "timed out" in (result.error_message or "")
    assert len(result.force_history) > 0


# ------------------------------------------------------------------
# PrimitiveLibrary integration
# ------------------------------------------------------------------


async def test_library_dispatches_to_real_path() -> None:
    """PrimitiveLibrary dispatches to real implementations with robot."""
    lib = PrimitiveLibrary()
    robot = MockRobot()
    result = await lib.run("move_to", robot, {"target_pose": [0.0] * 7, "timeout": 3.0})
    assert result.success
    assert len(result.force_history) > 0


async def test_library_dispatches_mock_path() -> None:
    """PrimitiveLibrary dispatches to mock path with robot=None."""
    lib = PrimitiveLibrary()
    result = await lib.run("move_to", None, {"target_pose": [0.0] * 7, "timeout": 0.1})
    assert result.success
    assert result.force_history == []
