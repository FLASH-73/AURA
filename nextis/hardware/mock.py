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

import numpy as np

from nextis.assembly.models import AssemblyStep
from nextis.perception.types import ExecutionData

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

    def generate_execution_data(
        self,
        step: AssemblyStep,
        *,
        force_success: bool | None = None,
    ) -> ExecutionData:
        """Generate realistic mock telemetry for verification testing.

        Reads ``step.success_criteria`` to produce data that the corresponding
        checker will evaluate as pass or fail.

        Args:
            step: Assembly step whose criteria determine the data shape.
            force_success: If ``True``, always produce passing data.  If
                ``False``, always failing.  If ``None`` (default), 80 %
                chance of success.
        """
        succeed = force_success if force_success is not None else (random.random() < 0.8)
        criteria = step.success_criteria
        params = step.primitive_params or {}
        target_pose = params.get("target_pose", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        duration_ms = random.uniform(500, 3000)

        if criteria.type == "force_threshold":
            return self._gen_force_threshold(criteria.threshold, target_pose, succeed, duration_ms)
        if criteria.type == "position":
            return self._gen_position(target_pose, succeed, duration_ms)
        if criteria.type == "force_signature":
            return self._gen_force_signature(
                criteria.pattern, criteria.threshold, target_pose, succeed, duration_ms
            )
        # classifier or unknown — return minimal data
        return ExecutionData(duration_ms=duration_ms)

    # -- private generators ---------------------------------------------------

    def _gen_force_threshold(
        self,
        threshold: float | None,
        target_pose: list[float],
        succeed: bool,
        duration_ms: float,
    ) -> ExecutionData:
        """Force-threshold criteria: ramp to peak above or below threshold."""
        thr = threshold or 1.0
        if succeed:
            peak = thr * 1.2
            force_history = list(np.linspace(thr * 0.1, peak, 30))
        else:
            peak = thr * 0.6
            force_history = list(np.random.uniform(thr * 0.1, peak, 30))
        return ExecutionData(
            final_position=list(target_pose[:3]),
            force_history=force_history,
            peak_force=float(max(force_history)),
            final_force=float(force_history[-1]),
            duration_ms=duration_ms,
        )

    def _gen_position(
        self,
        target_pose: list[float],
        succeed: bool,
        duration_ms: float,
    ) -> ExecutionData:
        """Position criteria: final position near or far from target."""
        target = np.array(target_pose[:3], dtype=np.float64)
        if succeed:
            offset = np.random.uniform(-0.3, 0.3, 3)
        else:
            offset = np.zeros(3)
            offset[random.randint(0, 2)] = 5.0
        final = target + offset
        noise = list(np.random.uniform(0.0, 0.5, 20))
        return ExecutionData(
            final_position=final.tolist(),
            force_history=noise,
            peak_force=float(max(noise)),
            final_force=float(noise[-1]),
            duration_ms=duration_ms,
        )

    def _gen_force_signature(
        self,
        pattern: str | None,
        threshold: float | None,
        target_pose: list[float],
        succeed: bool,
        duration_ms: float,
    ) -> ExecutionData:
        """Force-signature criteria: snap_fit / meshing / press_fit patterns."""
        if pattern == "snap_fit":
            fh = self._gen_snap_fit(succeed)
        elif pattern == "meshing":
            fh = self._gen_meshing(succeed)
        elif pattern == "press_fit":
            fh = self._gen_press_fit(threshold, succeed)
        else:
            fh = list(np.random.uniform(0.0, 0.3, 20))
        return ExecutionData(
            final_position=list(target_pose[:3]),
            force_history=fh,
            peak_force=float(max(fh)) if fh else 0.0,
            final_force=float(fh[-1]) if fh else 0.0,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _gen_snap_fit(succeed: bool) -> list[float]:
        """Snap-fit: peak then sharp drop, or flat noise."""
        if succeed:
            ramp = np.linspace(0.5, 5.0, 16).tolist()
            drop = [2.0, 1.5, 1.2, 1.1]
            hold = [1.0 + random.uniform(-0.1, 0.1) for _ in range(10)]
            return ramp + drop + hold
        return [random.uniform(0.0, 0.05) for _ in range(30)]

    @staticmethod
    def _gen_meshing(succeed: bool) -> list[float]:
        """Meshing: oscillating peaks, or monotonic rise."""
        if succeed:
            return [1.5 + 1.2 * math.sin(i * math.pi / 4) for i in range(40)]
        return list(np.linspace(0.1, 2.0, 30))

    @staticmethod
    def _gen_press_fit(threshold: float | None, succeed: bool) -> list[float]:
        """Press-fit: monotonic rise to target, or plateau below."""
        thr = threshold or 5.0
        if succeed:
            base = np.linspace(0.2, thr * 1.1, 30)
            jitter = np.random.uniform(-0.05, 0.05, 30)
            return (base + jitter).tolist()
        # Ramp to 40% then plateau
        ramp = np.linspace(0.2, thr * 0.4, 10).tolist()
        plateau = [thr * 0.4 + random.uniform(-0.3, 0.3) for _ in range(10)]
        return ramp + plateau

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
