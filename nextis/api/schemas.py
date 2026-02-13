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
    step_states: dict[str, StepRuntimeState] = Field(default_factory=dict, alias="stepStates")
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


# ------------------------------------------------------------------
# Teleop schemas
# ------------------------------------------------------------------


class TeleopStartRequest(BaseModel):
    """Request body for starting teleoperation."""

    model_config = ConfigDict(populate_by_name=True)

    arms: list[str] = Field(default_factory=lambda: ["default"])


class TeleopState(BaseModel):
    """Current teleoperation state."""

    model_config = ConfigDict(populate_by_name=True)

    active: bool = False
    arms: list[str] = Field(default_factory=list)
    session_id: str | None = Field(None, alias="sessionId")
    mock: bool = False
    loop_count: int = Field(0, alias="loopCount")


# ------------------------------------------------------------------
# Recording schemas
# ------------------------------------------------------------------


class RecordingStartRequest(BaseModel):
    """Request body for starting a recording session."""

    model_config = ConfigDict(populate_by_name=True)

    assembly_id: str = Field(alias="assemblyId")


class DemoInfo(BaseModel):
    """Metadata about a recorded demonstration."""

    model_config = ConfigDict(populate_by_name=True)

    demo_id: str = Field(alias="demoId")
    assembly_id: str = Field(alias="assemblyId")
    step_id: str = Field(alias="stepId")
    num_frames: int = Field(0, alias="numFrames")
    duration_s: float = Field(0.0, alias="durationS")
    file_path: str = Field("", alias="filePath")
    timestamp: float = 0.0


# ------------------------------------------------------------------
# Training schemas
# ------------------------------------------------------------------


class TrainRequest(BaseModel):
    """Request body for launching step-policy training."""

    model_config = ConfigDict(populate_by_name=True)

    architecture: str = "act"
    num_steps: int = Field(10_000, alias="numSteps")
    assembly_id: str = Field(alias="assemblyId")


class TrainingJobState(BaseModel):
    """State of a training job."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    step_id: str = Field(alias="stepId")
    status: str = "pending"
    progress: float = 0.0
    error: str | None = None


# ------------------------------------------------------------------
# AI Planning schemas
# ------------------------------------------------------------------


class PlanSuggestionResponse(BaseModel):
    """A single AI-suggested change to the assembly plan."""

    model_config = ConfigDict(populate_by_name=True)

    step_id: str = Field(alias="stepId")
    field: str
    old_value: str = Field(alias="oldValue")
    new_value: str = Field(alias="newValue")
    reason: str


class PlanAnalysisResponse(BaseModel):
    """Full AI analysis of an assembly plan."""

    model_config = ConfigDict(populate_by_name=True)

    suggestions: list[PlanSuggestionResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    difficulty_score: int = Field(5, alias="difficultyScore")
    estimated_teaching_minutes: int = Field(0, alias="estimatedTeachingMinutes")
    summary: str = ""
