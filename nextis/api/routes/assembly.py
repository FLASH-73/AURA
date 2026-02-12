"""Assembly CRUD routes.

Assemblies are stored as JSON files in configs/assemblies/.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from nextis.api.schemas import AssemblySummary
from nextis.assembly.models import AssemblyGraph

logger = logging.getLogger(__name__)

router = APIRouter()

CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs" / "assemblies"


def _find_assembly_path(assembly_id: str) -> Path:
    """Resolve an assembly ID to its JSON file path.

    Args:
        assembly_id: The assembly identifier.

    Returns:
        Path to the JSON file.

    Raises:
        HTTPException: If the assembly file does not exist.
    """
    path = CONFIGS_DIR / f"{assembly_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Assembly '{assembly_id}' not found")
    return path


def _load_assembly(assembly_id: str) -> AssemblyGraph:
    """Load and validate an assembly from disk."""
    path = _find_assembly_path(assembly_id)
    return AssemblyGraph.from_json_file(path)


@router.get("", response_model=list[AssemblySummary])
async def list_assemblies() -> list[AssemblySummary]:
    """List all assemblies (id + name only)."""
    summaries: list[AssemblySummary] = []
    for json_file in sorted(CONFIGS_DIR.glob("*.json")):
        try:
            graph = AssemblyGraph.from_json_file(json_file)
            summaries.append(AssemblySummary(id=graph.id, name=graph.name))
        except Exception:
            logger.warning("Failed to load assembly from %s", json_file, exc_info=True)
    return summaries


@router.get("/{assembly_id}")
async def get_assembly(assembly_id: str) -> dict[str, Any]:
    """Get the full assembly graph by ID."""
    graph = _load_assembly(assembly_id)
    return graph.model_dump(by_alias=True)


@router.post("", status_code=201)
async def create_assembly(graph: AssemblyGraph) -> dict[str, str]:
    """Create a new assembly from a full graph definition."""
    path = CONFIGS_DIR / f"{graph.id}.json"
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Assembly '{graph.id}' already exists")
    graph.to_json_file(path)
    logger.info("Created assembly %s", graph.id)
    return {"status": "created", "id": graph.id}


@router.patch("/{assembly_id}/steps/{step_id}")
async def update_step(
    assembly_id: str,
    step_id: str,
    updates: dict[str, Any],
) -> dict[str, str]:
    """Partially update a single step in an assembly."""
    graph = _load_assembly(assembly_id)
    if step_id not in graph.steps:
        raise HTTPException(status_code=404, detail=f"Step '{step_id}' not found")

    step = graph.steps[step_id]
    updated_data = step.model_dump(by_alias=True)
    updated_data.update(updates)
    graph.steps[step_id] = type(step).model_validate(updated_data)

    path = CONFIGS_DIR / f"{assembly_id}.json"
    graph.to_json_file(path)
    logger.info("Updated step %s in assembly %s", step_id, assembly_id)
    return {"status": "updated"}
