"""Analytics stub routes.

Returns empty metrics until the analytics layer is built.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from nextis.api.schemas import StepMetrics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{assembly_id}/steps", response_model=list[StepMetrics])
async def get_step_metrics(assembly_id: str) -> list[StepMetrics]:
    """Get per-step metrics for an assembly (empty stub)."""
    logger.debug("Step metrics requested for assembly %s", assembly_id)
    return []
