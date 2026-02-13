"""Execution layer type definitions.

Shared types used by the sequencer, policy router, and primitive library.
Defined separately to avoid circular imports between modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StepResult:
    """Result from executing a single assembly step.

    Attributes:
        success: Whether the step completed successfully.
        duration_ms: Execution time in milliseconds.
        handler_used: Either "primitive", "policy", or "stub".
        error_message: Description of failure, if any.
        actual_force: Peak force/torque measured during step (Nm).
        actual_position: Joint positions at step completion.
        force_history: Per-tick joint torques captured during step execution.
    """

    success: bool
    duration_ms: float
    handler_used: str
    error_message: str | None = None
    actual_force: float = 0.0
    actual_position: list[float] = field(default_factory=list)
    force_history: list[list[float]] = field(default_factory=list)
