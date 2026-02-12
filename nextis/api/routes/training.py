"""Training job stub routes.

Placeholder for per-step policy training.  Returns stub responses until
the training pipeline is built in a future iteration.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException

from nextis.api.schemas import TrainingJobState, TrainRequest

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job registry (stub — no actual training runs).
_jobs: dict[str, TrainingJobState] = {}


@router.post("/step/{step_id}/train")
async def start_training(step_id: str, request: TrainRequest) -> TrainingJobState:
    """Launch a training job for a specific assembly step (stub).

    Accepts the request and creates a job entry but does not run training.

    Args:
        step_id: Assembly step to train a policy for.
        request: Training configuration.
    """
    job_id = str(uuid.uuid4())[:8]

    job = TrainingJobState(
        job_id=job_id,
        step_id=step_id,
        status="pending",
        progress=0.0,
    )
    _jobs[job_id] = job

    logger.info(
        "Training job created (stub): job=%s step=%s arch=%s steps=%d",
        job_id,
        step_id,
        request.architecture,
        request.num_steps,
    )
    return job


@router.get("/jobs/{job_id}")
async def get_training_job(job_id: str) -> TrainingJobState:
    """Get the status of a training job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Training job '{job_id}' not found")
    return job


@router.get("/jobs", response_model=list[TrainingJobState])
async def list_training_jobs() -> list[TrainingJobState]:
    """List all training jobs."""
    return list(_jobs.values())
