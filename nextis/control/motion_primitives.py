"""Real motion primitive implementations.

Each primitive has a dual path:
- **Mock** (``robot is None``): sleep and return fake success (unchanged from stubs).
- **Real** (``robot`` connected): 60 Hz control loop with force monitoring.

All primitives record ``force_history`` (per-tick joint torques) and return
real sensor data in :class:`PrimitiveResult`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from nextis.control.motion_helpers import (
    CONTROL_DT,
    GRIPPER_CLOSED,
    GRIPPER_OPEN,
    PrimitiveResult,
    interpolate_step,
    joints_to_action,
    obs_to_joints,
    pad_target,
    peak_abs_torque,
    position_reached,
    read_torques_list,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# move_to
# ---------------------------------------------------------------------------


async def move_to(
    robot: Any,
    target_pose: list[float] | None = None,
    velocity: float = 0.5,
    timeout: float = 10.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Move joints to a target pose via interpolation.

    Args:
        robot: Connected follower robot instance (None for mock).
        target_pose: Target joint positions (padded if shorter than 7).
        velocity: Movement speed factor (0.0–1.0).
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with actual position and force history.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    target_pose = target_pose or []
    logger.info("move_to: target=%s velocity=%.2f", target_pose, velocity)
    start = time.monotonic()

    # Mock path
    if robot is None:
        await asyncio.sleep(min(1.0, timeout) * speed)
        duration = (time.monotonic() - start) * 1000
        logger.info("move_to: complete in %.0fms (mock)", duration)
        return PrimitiveResult(success=True, actual_position=target_pose, duration_ms=duration)

    # Real path
    current = obs_to_joints(robot.get_observation())
    target = pad_target(target_pose, current)
    forces: list[list[float]] = []

    while (time.monotonic() - start) < timeout:
        current = obs_to_joints(robot.get_observation())
        torques = read_torques_list(robot)
        forces.append(torques)

        if position_reached(current, target):
            duration = (time.monotonic() - start) * 1000
            logger.info("move_to: converged in %.0fms", duration)
            return PrimitiveResult(
                success=True,
                actual_position=current,
                actual_force=peak_abs_torque(torques),
                duration_ms=duration,
                force_history=forces,
            )

        alpha = min(1.0, velocity * CONTROL_DT * 2.0)
        command = interpolate_step(current, target, alpha)
        robot.send_action(joints_to_action(command))
        await asyncio.sleep(CONTROL_DT)

    # Timeout
    duration = (time.monotonic() - start) * 1000
    logger.warning("move_to: timed out after %.0fms", duration)
    return PrimitiveResult(
        success=False,
        actual_position=current,
        actual_force=peak_abs_torque(forces[-1]) if forces else 0.0,
        duration_ms=duration,
        error_message=f"move_to timed out after {timeout:.1f}s",
        force_history=forces,
    )


# ---------------------------------------------------------------------------
# pick
# ---------------------------------------------------------------------------


async def pick(
    robot: Any,
    grasp_pose: list[float] | None = None,
    approach_height: float = 0.05,
    force_threshold: float = 0.5,
    timeout: float = 15.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Pick a part: move to grasp pose, close gripper until force threshold.

    Args:
        robot: Connected follower robot instance (None for mock).
        grasp_pose: Target joint positions for the grasp.
        approach_height: Not used in joint-space mode (reserved for Cartesian).
        force_threshold: Gripper torque (Nm) to confirm a successful grasp.
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with measured grip force.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    logger.info(
        "pick: grasp_pose=%s approach=%.3fm threshold=%.2fNm",
        grasp_pose,
        approach_height,
        force_threshold,
    )
    start = time.monotonic()

    # Mock path
    if robot is None:
        await asyncio.sleep(min(1.5, timeout) * speed)
        duration = (time.monotonic() - start) * 1000
        logger.info("pick: complete in %.0fms (mock)", duration)
        return PrimitiveResult(
            success=True,
            actual_force=force_threshold,
            actual_position=grasp_pose or [],
            duration_ms=duration,
        )

    # Real path — Phase 1: move to grasp pose
    move_timeout = timeout * 0.6
    move_result = await move_to(robot, target_pose=grasp_pose, velocity=0.5, timeout=move_timeout)
    forces: list[list[float]] = list(move_result.force_history)
    if not move_result.success:
        move_result.error_message = (
            f"pick: failed to reach grasp pose — {move_result.error_message}"
        )
        move_result.force_history = forces
        return move_result

    # Phase 2: close gripper until force threshold
    current = obs_to_joints(robot.get_observation())
    while (time.monotonic() - start) < timeout:
        torques = read_torques_list(robot)
        forces.append(torques)
        gripper_torque = abs(torques[6])  # gripper is last in JOINT_ORDER

        if gripper_torque >= force_threshold:
            duration = (time.monotonic() - start) * 1000
            logger.info("pick: grasped at %.2fNm in %.0fms", gripper_torque, duration)
            return PrimitiveResult(
                success=True,
                actual_force=gripper_torque,
                actual_position=obs_to_joints(robot.get_observation()),
                duration_ms=duration,
                force_history=forces,
            )

        # Close gripper, hold other joints
        command = list(current)
        command[6] = GRIPPER_CLOSED
        robot.send_action(joints_to_action(command))
        await asyncio.sleep(CONTROL_DT)

    duration = (time.monotonic() - start) * 1000
    logger.warning("pick: force threshold not reached in %.0fms", duration)
    return PrimitiveResult(
        success=False,
        actual_force=abs(read_torques_list(robot)[6]),
        actual_position=obs_to_joints(robot.get_observation()),
        duration_ms=duration,
        error_message=f"Gripper force below threshold {force_threshold:.2f}Nm",
        force_history=forces,
    )


# ---------------------------------------------------------------------------
# place
# ---------------------------------------------------------------------------


async def place(
    robot: Any,
    target_pose: list[float] | None = None,
    approach_height: float = 0.05,
    release_force: float = 0.2,
    timeout: float = 15.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Place a part: move to target pose, open gripper, retract.

    Args:
        robot: Connected follower robot instance (None for mock).
        target_pose: Target joint positions for placement.
        approach_height: Not used in joint-space mode (reserved for Cartesian).
        release_force: Gripper torque (Nm) below which release is confirmed.
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with actual position.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    target_pose = target_pose or []
    logger.info("place: target=%s approach=%.3fm", target_pose, approach_height)
    start = time.monotonic()

    # Mock path
    if robot is None:
        await asyncio.sleep(min(1.5, timeout) * speed)
        duration = (time.monotonic() - start) * 1000
        logger.info("place: complete in %.0fms (mock)", duration)
        return PrimitiveResult(success=True, actual_position=target_pose, duration_ms=duration)

    # Real path — Phase 1: move to placement pose
    move_timeout = timeout * 0.6
    move_result = await move_to(robot, target_pose=target_pose, velocity=0.5, timeout=move_timeout)
    forces: list[list[float]] = list(move_result.force_history)
    if not move_result.success:
        move_result.error_message = f"place: failed to reach target — {move_result.error_message}"
        move_result.force_history = forces
        return move_result

    # Phase 2: open gripper
    current = obs_to_joints(robot.get_observation())
    while (time.monotonic() - start) < timeout:
        torques = read_torques_list(robot)
        forces.append(torques)
        gripper_torque = abs(torques[6])

        if gripper_torque <= release_force:
            duration = (time.monotonic() - start) * 1000
            logger.info("place: released at %.2fNm in %.0fms", gripper_torque, duration)
            return PrimitiveResult(
                success=True,
                actual_position=obs_to_joints(robot.get_observation()),
                actual_force=gripper_torque,
                duration_ms=duration,
                force_history=forces,
            )

        command = list(current)
        command[6] = GRIPPER_OPEN
        robot.send_action(joints_to_action(command))
        await asyncio.sleep(CONTROL_DT)

    duration = (time.monotonic() - start) * 1000
    logger.warning("place: gripper release not confirmed in %.0fms", duration)
    return PrimitiveResult(
        success=False,
        actual_position=obs_to_joints(robot.get_observation()),
        duration_ms=duration,
        error_message=f"Gripper force above release threshold {release_force:.2f}Nm",
        force_history=forces,
    )


# ---------------------------------------------------------------------------
# guarded_move
# ---------------------------------------------------------------------------


async def guarded_move(
    robot: Any,
    direction: list[float] | None = None,
    force_threshold: float = 5.0,
    max_distance: float = 0.1,
    timeout: float = 10.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Move in a direction until a force threshold is hit.

    Args:
        robot: Connected follower robot instance (None for mock).
        direction: Per-joint velocity direction vector (first 6 joints).
        force_threshold: Torque (Nm) at which to stop.
        max_distance: Maximum cumulative joint displacement.
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with contact force.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    direction = direction or [0, 0, -1]
    logger.info(
        "guarded_move: dir=%s threshold=%.1fNm max=%.3f",
        direction,
        force_threshold,
        max_distance,
    )
    start = time.monotonic()

    # Mock path
    if robot is None:
        await asyncio.sleep(min(1.0, timeout) * speed)
        duration = (time.monotonic() - start) * 1000
        logger.info("guarded_move: contact at %.1fNm in %.0fms (mock)", force_threshold, duration)
        return PrimitiveResult(
            success=True,
            actual_force=force_threshold,
            duration_ms=duration,
        )

    # Real path — step along direction until force contact
    current = obs_to_joints(robot.get_observation())
    origin = list(current)
    forces: list[list[float]] = []
    # Normalize direction to 7 joints (pad with zeros for gripper)
    dir_padded = list(direction) + [0.0] * max(0, 7 - len(direction))
    step_size = CONTROL_DT * 0.5  # joint displacement per tick

    while (time.monotonic() - start) < timeout:
        current = obs_to_joints(robot.get_observation())
        torques = read_torques_list(robot)
        forces.append(torques)

        # Check force threshold (peak across non-gripper joints)
        peak = peak_abs_torque(torques[:6])
        if peak >= force_threshold:
            duration = (time.monotonic() - start) * 1000
            logger.info("guarded_move: contact at %.2fNm in %.0fms", peak, duration)
            return PrimitiveResult(
                success=True,
                actual_force=peak,
                actual_position=current,
                duration_ms=duration,
                force_history=forces,
            )

        # Check max distance
        displacement = sum((c - o) ** 2 for c, o in zip(current, origin, strict=False)) ** 0.5
        if displacement >= max_distance:
            duration = (time.monotonic() - start) * 1000
            logger.info("guarded_move: max distance reached without contact")
            return PrimitiveResult(
                success=False,
                actual_force=peak,
                actual_position=current,
                duration_ms=duration,
                error_message=f"Max distance {max_distance:.3f} reached without force contact",
                force_history=forces,
            )

        # Step in direction
        command = [c + d * step_size for c, d in zip(current, dir_padded, strict=False)]
        robot.send_action(joints_to_action(command))
        await asyncio.sleep(CONTROL_DT)

    duration = (time.monotonic() - start) * 1000
    logger.warning("guarded_move: timed out after %.0fms", duration)
    return PrimitiveResult(
        success=False,
        actual_position=current,
        duration_ms=duration,
        error_message=f"guarded_move timed out after {timeout:.1f}s",
        force_history=forces,
    )


# ---------------------------------------------------------------------------
# linear_insert
# ---------------------------------------------------------------------------


async def linear_insert(
    robot: Any,
    target_pose: list[float] | None = None,
    force_limit: float = 10.0,
    compliance_axes: list[bool] | None = None,
    timeout: float = 15.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Insert along a linear path with force limiting.

    Args:
        robot: Connected follower robot instance (None for mock).
        target_pose: Target joint positions for insertion endpoint.
        force_limit: Maximum allowed insertion torque (Nm).
        compliance_axes: Per-joint compliance flags (True = compliant).
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with final position and force.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    target_pose = target_pose or []
    logger.info("linear_insert: target=%s force_limit=%.1fNm", target_pose, force_limit)
    start = time.monotonic()

    # Mock path
    if robot is None:
        await asyncio.sleep(min(2.0, timeout) * speed)
        duration = (time.monotonic() - start) * 1000
        logger.info("linear_insert: complete in %.0fms (mock)", duration)
        return PrimitiveResult(
            success=True,
            actual_force=force_limit * 0.6,
            actual_position=target_pose,
            duration_ms=duration,
        )

    # Real path — interpolate toward target, monitoring force
    current = obs_to_joints(robot.get_observation())
    target = pad_target(target_pose, current)
    compliant = compliance_axes or [False] * 7
    forces: list[list[float]] = []

    while (time.monotonic() - start) < timeout:
        current = obs_to_joints(robot.get_observation())
        torques = read_torques_list(robot)
        forces.append(torques)
        peak = peak_abs_torque(torques[:6])

        # Force limit — confirms part is seated
        if peak >= force_limit:
            duration = (time.monotonic() - start) * 1000
            logger.info("linear_insert: force limit at %.2fNm in %.0fms", peak, duration)
            return PrimitiveResult(
                success=True,
                actual_force=peak,
                actual_position=current,
                duration_ms=duration,
                force_history=forces,
            )

        # Position convergence
        if position_reached(current, target):
            duration = (time.monotonic() - start) * 1000
            logger.info("linear_insert: position reached in %.0fms", duration)
            return PrimitiveResult(
                success=True,
                actual_force=peak,
                actual_position=current,
                duration_ms=duration,
                force_history=forces,
            )

        # Interpolate toward target; skip compliant axes (hold position)
        alpha = min(1.0, CONTROL_DT * 1.0)
        command = list(current)
        for i in range(min(len(target), len(current))):
            if i < len(compliant) and compliant[i]:
                continue  # compliant — hold position
            command[i] = current[i] + alpha * (target[i] - current[i])
        robot.send_action(joints_to_action(command))
        await asyncio.sleep(CONTROL_DT)

    duration = (time.monotonic() - start) * 1000
    logger.warning("linear_insert: timed out after %.0fms", duration)
    return PrimitiveResult(
        success=False,
        actual_position=current,
        actual_force=peak_abs_torque(forces[-1]) if forces else 0.0,
        duration_ms=duration,
        error_message=f"linear_insert timed out after {timeout:.1f}s",
        force_history=forces,
    )


# ---------------------------------------------------------------------------
# screw
# ---------------------------------------------------------------------------


async def screw(
    robot: Any,
    target_pose: list[float] | None = None,
    torque_limit: float = 2.0,
    rotations: float = 3.0,
    timeout: float = 20.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Screw operation with torque-based termination.

    Rotates the wrist joint (link5) while holding other joints steady,
    monitoring torque until the limit is reached or rotations are complete.

    Args:
        robot: Connected follower robot instance (None for mock).
        target_pose: Base joint pose to hold during screwing.
        torque_limit: Maximum allowed torque on the wrist (Nm).
        rotations: Number of full rotations to attempt.
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with final torque reading.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    logger.info("screw: rotations=%.1f torque_limit=%.1fNm", rotations, torque_limit)
    start = time.monotonic()

    # Mock path
    if robot is None:
        await asyncio.sleep(min(2.0, timeout) * speed)
        duration = (time.monotonic() - start) * 1000
        logger.info("screw: complete in %.0fms (mock)", duration)
        return PrimitiveResult(success=True, actual_force=torque_limit * 0.8, duration_ms=duration)

    # Real path — rotate wrist incrementally
    import math

    current = obs_to_joints(robot.get_observation())
    wrist_start = current[5]  # link5 is the wrist
    total_angle = rotations * 2 * math.pi
    rotation_speed = 0.5  # rad/s
    forces: list[list[float]] = []

    while (time.monotonic() - start) < timeout:
        current = obs_to_joints(robot.get_observation())
        torques = read_torques_list(robot)
        forces.append(torques)
        wrist_torque = abs(torques[5])  # link5 torque

        # Torque limit reached
        if wrist_torque >= torque_limit:
            duration = (time.monotonic() - start) * 1000
            logger.info("screw: torque limit at %.2fNm in %.0fms", wrist_torque, duration)
            return PrimitiveResult(
                success=True,
                actual_force=wrist_torque,
                actual_position=current,
                duration_ms=duration,
                force_history=forces,
            )

        # Check if rotations complete
        wrist_delta = abs(current[5] - wrist_start)
        if wrist_delta >= total_angle:
            duration = (time.monotonic() - start) * 1000
            logger.info("screw: %.1f rotations complete in %.0fms", rotations, duration)
            return PrimitiveResult(
                success=True,
                actual_force=wrist_torque,
                actual_position=current,
                duration_ms=duration,
                force_history=forces,
            )

        # Increment wrist, hold other joints
        command = list(current)
        command[5] += rotation_speed * CONTROL_DT
        robot.send_action(joints_to_action(command))
        await asyncio.sleep(CONTROL_DT)

    duration = (time.monotonic() - start) * 1000
    logger.warning("screw: timed out after %.0fms", duration)
    return PrimitiveResult(
        success=False,
        actual_position=current,
        actual_force=abs(read_torques_list(robot)[5]),
        duration_ms=duration,
        error_message=f"screw timed out after {timeout:.1f}s",
        force_history=forces,
    )


# ---------------------------------------------------------------------------
# press_fit
# ---------------------------------------------------------------------------


async def press_fit(
    robot: Any,
    direction: list[float] | None = None,
    force_target: float = 15.0,
    max_distance: float = 0.02,
    timeout: float = 15.0,
    **kwargs: Any,
) -> PrimitiveResult:
    """Press-fit: push along direction until target force is reached.

    Args:
        robot: Connected follower robot instance (None for mock).
        direction: Per-joint velocity direction vector.
        force_target: Target pressing force (Nm) for success.
        max_distance: Maximum cumulative joint displacement.
        timeout: Maximum execution time in seconds.

    Returns:
        PrimitiveResult with achieved pressing force.
    """
    speed = kwargs.pop("_speed_factor", 1.0)
    direction = direction or [0, 0, -1]
    logger.info(
        "press_fit: dir=%s target=%.1fNm max=%.3fm",
        direction,
        force_target,
        max_distance,
    )
    start = time.monotonic()

    # Mock path
    if robot is None:
        await asyncio.sleep(min(1.5, timeout) * speed)
        duration = (time.monotonic() - start) * 1000
        logger.info("press_fit: complete at %.1fNm in %.0fms (mock)", force_target, duration)
        return PrimitiveResult(success=True, actual_force=force_target, duration_ms=duration)

    # Real path — push until force target
    current = obs_to_joints(robot.get_observation())
    origin = list(current)
    forces: list[list[float]] = []
    dir_padded = list(direction) + [0.0] * max(0, 7 - len(direction))
    step_size = CONTROL_DT * 0.3  # slower push than guarded_move

    while (time.monotonic() - start) < timeout:
        current = obs_to_joints(robot.get_observation())
        torques = read_torques_list(robot)
        forces.append(torques)
        peak = peak_abs_torque(torques[:6])

        # Target force reached
        if peak >= force_target:
            duration = (time.monotonic() - start) * 1000
            logger.info("press_fit: target force %.2fNm in %.0fms", peak, duration)
            return PrimitiveResult(
                success=True,
                actual_force=peak,
                actual_position=current,
                duration_ms=duration,
                force_history=forces,
            )

        # Max distance exceeded
        displacement = sum((c - o) ** 2 for c, o in zip(current, origin, strict=False)) ** 0.5
        if displacement >= max_distance:
            duration = (time.monotonic() - start) * 1000
            logger.warning("press_fit: max distance without target force")
            return PrimitiveResult(
                success=False,
                actual_force=peak,
                actual_position=current,
                duration_ms=duration,
                error_message=(
                    f"Max distance {max_distance:.3f} reached "
                    f"(force {peak:.2f}Nm < target {force_target:.2f}Nm)"
                ),
                force_history=forces,
            )

        command = [c + d * step_size for c, d in zip(current, dir_padded, strict=False)]
        robot.send_action(joints_to_action(command))
        await asyncio.sleep(CONTROL_DT)

    duration = (time.monotonic() - start) * 1000
    logger.warning("press_fit: timed out after %.0fms", duration)
    return PrimitiveResult(
        success=False,
        actual_position=current,
        actual_force=peak_abs_torque(forces[-1]) if forces else 0.0,
        duration_ms=duration,
        error_message=f"press_fit timed out after {timeout:.1f}s",
        force_history=forces,
    )
