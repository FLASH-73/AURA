"""API response schemas for execution state and analytics.

These Pydantic models match the TypeScript interfaces in frontend/lib/types.ts.
All use camelCase aliases for JSON serialization.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AssemblySummary(BaseModel):
    """Lightweight assembly reference for list endpoints."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str


class StepRuntimeState(BaseModel):
    """Per-step execution state during a run."""

    model_config = ConfigDict(populate_by_name=True)

    step_id: str = Field(alias="stepId")
    status: str = "pending"
    attempt: int = 1
    start_time: float | None = Field(None, alias="startTime")
    end_time: float | None = Field(None, alias="endTime")
    duration_ms: float | None = Field(None, alias="durationMs")


class ExecutionState(BaseModel):
    """Full sequencer state matching the frontend ExecutionState interface."""

    model_config = ConfigDict(populate_by_name=True)

    phase: str = "idle"
    assembly_id: str | None = Field(None, alias="assemblyId")
    current_step_id: str | None = Field(None, alias="currentStepId")
    step_states: dict[str, StepRuntimeState] = Field(
        default_factory=dict, alias="stepStates"
    )
    run_number: int = Field(0, alias="runNumber")
    start_time: float | None = Field(None, alias="startTime")
    elapsed_ms: float = Field(0, alias="elapsedMs")
    overall_success_rate: float = Field(0, alias="overallSuccessRate")


class RunEntry(BaseModel):
    """A single run result for step metrics history."""

    model_config = ConfigDict(populate_by_name=True)

    success: bool
    duration_ms: float = Field(alias="durationMs")
    timestamp: float


class StepMetrics(BaseModel):
    """Per-step analytics data."""

    model_config = ConfigDict(populate_by_name=True)

    step_id: str = Field(alias="stepId")
    success_rate: float = Field(0, alias="successRate")
    avg_duration_ms: float = Field(0, alias="avgDurationMs")
    total_attempts: int = Field(0, alias="totalAttempts")
    demo_count: int = Field(0, alias="demoCount")
    recent_runs: list[RunEntry] = Field(default_factory=list, alias="recentRuns")
