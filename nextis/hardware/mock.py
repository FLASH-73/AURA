"""Mock robot and leader for hardware-free testing.

Provides MockRobot and MockLeader that satisfy the interfaces consumed by
TeleopLoop, SafetyLayer, and JointMapper. Used when teleop is started with
``mock=True`` via the API.
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MOCK_JOINT_NAMES: list[str] = [
    "base",
    "link1",
    "link2",
    "link3",
    "link4",
    "link5",
    "gripper",
]


@dataclass
class MockCalibration:
    """Minimal calibration entry matching the TeleopLoop interface."""

    range_min: float = 0.0
    range_max: float = 4096.0


@dataclass
class _MockMotor:
    """Motor stub with an ID."""

    motor_id: int = field(default=0)

    @property
    def id(self) -> int:  # noqa: A003
        return self.motor_id


class MockBus:
    """Minimal bus stub satisfying robot.bus and leader.bus interfaces."""

    def __init__(self) -> None:
        self._last_positions: dict[str, float] = {n: 0.0 for n in MOCK_JOINT_NAMES}
        self._can_bus_dead: bool = False
        self._software_homing_offsets: dict[int, int] = {}
        self.motors: dict[str, _MockMotor] = {
            name: _MockMotor(motor_id=i) for i, name in enumerate(MOCK_JOINT_NAMES)
        }

    def write(self, register: str, motor_name: str, value: Any, **kwargs: Any) -> None:
        """No-op register write."""

    def write_pwm(self, pwm_dict: dict[str, int]) -> None:
        """No-op PWM write."""


class MockRobot:
    """Fake follower robot that obeys sent commands.

    When :meth:`send_action` has been called, subsequent :meth:`get_observation`
    calls return the commanded positions (mimicking a real robot that tracks
    commands). Before any action is sent, returns smooth sine-wave trajectories
    for backward compatibility with TeleopLoop tests.
    """

    def __init__(self) -> None:
        self.bus = MockBus()
        self.calibration: dict[str, MockCalibration] = {
            n: MockCalibration() for n in MOCK_JOINT_NAMES
        }
        self.is_connected: bool = True
        self._start_time = time.monotonic()
        self._commanded: dict[str, float] | None = None

    def get_observation(self) -> dict[str, float]:
        """Return joint positions.

        If :meth:`send_action` has been called, returns the last commanded
        positions (the robot "obeys"). Otherwise returns sine-wave positions
        for passive observation scenarios (e.g. TeleopLoop).
        """
        if self._commanded is not None:
            return dict(self._commanded)
        t = time.monotonic() - self._start_time
        return {
            f"{n}.pos": math.sin(t * 0.5 + i * 0.5) * 0.3 for i, n in enumerate(MOCK_JOINT_NAMES)
        }

    def send_action(self, action: dict[str, float]) -> None:
        """Accept action, update bus positions and commanded state."""
        self._commanded = dict(action)
        for key, val in action.items():
            self.bus._last_positions[key.replace(".pos", "")] = val

    def get_torques(self) -> dict[str, float]:
        """Return small random torques."""
        return {n: random.uniform(-0.1, 0.1) for n in MOCK_JOINT_NAMES}

    def get_torque_limits(self) -> dict[str, float]:
        """Return generous mock limits."""
        return {n: 10.0 for n in MOCK_JOINT_NAMES}

    def get_cached_positions(self) -> dict[str, float]:
        """Return current observation keyed by bare motor name."""
        obs = self.get_observation()
        return {k.replace(".pos", ""): v for k, v in obs.items()}

    def disconnect(self) -> None:
        """Mark as disconnected."""
        self.is_connected = False
        logger.info("MockRobot disconnected")


class MockLeader:
    """Fake leader arm producing smooth sine-wave actions.

    Satisfies the leader interface consumed by TeleopLoop.
    """

    def __init__(self) -> None:
        self.bus = MockBus()
        self._start_time = time.monotonic()

    def get_action(self) -> dict[str, float]:
        """Return sine-wave positions mimicking human motion."""
        t = time.monotonic() - self._start_time
        return {
            f"{n}.pos": math.sin(t * 0.3 + i * 0.7 + 1.0) * 0.2
            for i, n in enumerate(MOCK_JOINT_NAMES)
        }
