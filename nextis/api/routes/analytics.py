"""Analytics routes — per-step execution metrics.

Reads from the AnalyticsStore to return computed metrics per step.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from nextis.analytics.store import AnalyticsStore
from nextis.api.schemas import StepMetrics
from nextis.assembly.models import AssemblyGraph

logger = logging.getLogger(__name__)

router = APIRouter()

CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs" / "assemblies"
ANALYTICS_DIR = Path(__file__).resolve().parents[3] / "data" / "analytics"


@router.get("/{assembly_id}/steps", response_model=list[StepMetrics])
async def get_step_metrics(assembly_id: str) -> list[StepMetrics]:
    """Get per-step metrics for an assembly.

    Loads the assembly graph to get step IDs, then queries the
    analytics store for computed metrics per step.

    Args:
        assembly_id: Assembly identifier.

    Returns:
        List of StepMetrics, one per step in execution order.
    """
    path = CONFIGS_DIR / f"{assembly_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Assembly '{assembly_id}' not found")

    graph = AssemblyGraph.from_json_file(path)
    store = AnalyticsStore(root=ANALYTICS_DIR)
    return store.get_step_metrics_for(assembly_id, graph.step_order)
