"""Execution state stub routes.

These endpoints return placeholder data until the real sequencer is built.
The frontend calls these to avoid 404 errors.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from nextis.api.schemas import ExecutionState

logger = logging.getLogger(__name__)

router = APIRouter()


class StartRequest(BaseModel):
    """Request body for starting execution."""

    model_config = ConfigDict(populate_by_name=True)

    assembly_id: str = Field(alias="assemblyId")


@router.get("/state")
async def get_execution_state() -> dict:
    """Return the current execution state (idle stub)."""
    state = ExecutionState()
    return state.model_dump(by_alias=True)


@router.post("/start")
async def start_execution(request: StartRequest) -> dict[str, str]:
    """Start assembly execution (stub)."""
    logger.info("Start execution requested for assembly %s", request.assembly_id)
    return {"status": "ok"}


@router.post("/pause")
async def pause_execution() -> dict[str, str]:
    """Pause execution (stub)."""
    logger.info("Pause execution requested")
    return {"status": "ok"}


@router.post("/stop")
async def stop_execution() -> dict[str, str]:
    """Stop execution (stub)."""
    logger.info("Stop execution requested")
    return {"status": "ok"}


@router.post("/intervene")
async def intervene() -> dict[str, str]:
    """Signal human intervention (stub)."""
    logger.info("Human intervention requested")
    return {"status": "ok"}
