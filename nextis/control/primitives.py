"""Parameterized motion primitives for assembly execution.

Each primitive is an async function that takes a robot instance + parameters,
executes a motion using impedance control, and returns success/failure based
on force/position criteria. When ``robot`` is ``None`` (mock mode), primitives
sleep and return synthetic success so the sequencer and tests work without
hardware.

Real implementations live in :mod:`nextis.control.motion_primitives`.
This module re-exports them and provides :class:`PrimitiveResult` (via
:mod:`motion_helpers`) and :class:`PrimitiveLibrary`.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from nextis.control.motion_helpers import PrimitiveResult  # noqa: F401
from nextis.control.motion_primitives import (  # noqa: F401
    guarded_move,
    linear_insert,
    move_to,
    pick,
    place,
    press_fit,
    screw,
)
from nextis.errors import AssemblyError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Primitive library — registry and dispatcher
# ---------------------------------------------------------------------------

PrimitiveFn = Callable[..., Awaitable[PrimitiveResult]]


class PrimitiveLibrary:
    """Registry and dispatcher for motion primitives.

    Registers primitive functions by name and dispatches assembly step
    parameters to the appropriate primitive.
    """

    def __init__(self, speed_factor: float = 1.0) -> None:
        self._primitives: dict[str, PrimitiveFn] = {}
        self._speed = speed_factor
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all built-in primitives."""
        self.register("move_to", move_to)
        self.register("pick", pick)
        self.register("place", place)
        self.register("guarded_move", guarded_move)
        self.register("linear_insert", linear_insert)
        self.register("screw", screw)
        self.register("press_fit", press_fit)

    def register(self, name: str, fn: PrimitiveFn) -> None:
        """Register a primitive function by name.

        Args:
            name: Primitive identifier (e.g., "pick").
            fn: Async callable implementing the primitive.
        """
        self._primitives[name] = fn
        logger.debug("Registered primitive: %s", name)

    async def run(
        self,
        name: str,
        robot: Any,
        params: dict | None = None,
    ) -> PrimitiveResult:
        """Execute a primitive by name with given parameters.

        Args:
            name: Primitive name (e.g., "pick", "place").
            robot: Connected follower robot.
            params: Parameters passed as keyword arguments to the primitive.

        Returns:
            PrimitiveResult from the primitive execution.

        Raises:
            AssemblyError: If the primitive name is not registered.
        """
        fn = self._primitives.get(name)
        if fn is None:
            raise AssemblyError(f"Unknown primitive: {name}")
        params = params or {}
        params["_speed_factor"] = self._speed
        logger.info("Dispatching primitive '%s' with params: %s", name, params)
        return await fn(robot=robot, **params)

    @property
    def available(self) -> list[str]:
        """List registered primitive names."""
        return list(self._primitives.keys())
