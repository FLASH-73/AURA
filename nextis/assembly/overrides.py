"""Assembly override persistence.

Stores user and AI modifications to assembly plans as a separate JSON file.
Overrides are keyed by part IDs and step name patterns (not step_id, since
step IDs change on re-parse). On re-upload, overrides are matched against
the new plan and re-applied.

Override file location: configs/overrides/{assembly_id}.json
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from nextis.assembly.models import AssemblyGraph, AssemblyStep, SuccessCriteria

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class StepOverride(BaseModel):
    """A single override for an assembly step.

    Matching: An override matches a step if the step's name contains
    match_pattern (case-insensitive substring match) OR if the step's
    part_ids intersect with match_part_ids. If both are set, the step
    must satisfy BOTH criteria.

    Attributes:
        match_pattern: Substring to match against step.name.
        match_part_ids: Part IDs that the target step must involve.
        handler: Override handler ("primitive" or "policy"), or None to keep.
        primitive_type: Override primitive type, or None.
        primitive_params: Override params (merged with existing), or None.
        success_criteria: Override success criteria as dict, or None.
        max_retries: Override max retries, or None.
        policy_id: Override policy checkpoint path, or None.
        source: Who created this — "user" or "ai".
        created_at: ISO timestamp of creation.
    """

    model_config = ConfigDict(populate_by_name=True)

    match_pattern: str | None = Field(None, alias="matchPattern")
    match_part_ids: list[str] = Field(default_factory=list, alias="matchPartIds")
    handler: str | None = None
    primitive_type: str | None = Field(None, alias="primitiveType")
    primitive_params: dict | None = Field(None, alias="primitiveParams")
    success_criteria: dict | None = Field(None, alias="successCriteria")
    max_retries: int | None = Field(None, alias="maxRetries")
    policy_id: str | None = Field(None, alias="policyId")
    source: str = "user"
    created_at: str = Field(default="", alias="createdAt")


class AssemblyOverrides(BaseModel):
    """Collection of overrides for an assembly.

    Attributes:
        assembly_id: The assembly these overrides belong to.
        overrides: List of step overrides.
    """

    model_config = ConfigDict(populate_by_name=True)

    assembly_id: str = Field(alias="assemblyId")
    overrides: list[StepOverride] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class OverrideStore:
    """Filesystem-backed override persistence.

    One JSON file per assembly at ``{base_dir}/{assembly_id}.json``.

    Args:
        base_dir: Directory for override JSON files.
            Defaults to ``configs/overrides/`` relative to the repo root.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or (Path(__file__).resolve().parents[2] / "configs" / "overrides")
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- persistence --------------------------------------------------------

    def save(self, overrides: AssemblyOverrides) -> None:
        """Save overrides to disk.

        Args:
            overrides: The overrides collection to persist.
        """
        path = self._dir / f"{overrides.assembly_id}.json"
        path.write_text(overrides.model_dump_json(by_alias=True, indent=2) + "\n")
        logger.debug("Saved %d overrides for %s", len(overrides.overrides), overrides.assembly_id)

    def load(self, assembly_id: str) -> AssemblyOverrides | None:
        """Load overrides from disk.

        Args:
            assembly_id: The assembly to load overrides for.

        Returns:
            Parsed overrides, or None if no file exists.
        """
        path = self._dir / f"{assembly_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return AssemblyOverrides.model_validate(data)
        except (json.JSONDecodeError, Exception):
            logger.warning("Corrupt override file %s, ignoring", path, exc_info=True)
            return None

    def delete(self, assembly_id: str) -> bool:
        """Delete all overrides for an assembly.

        Args:
            assembly_id: The assembly whose overrides to remove.

        Returns:
            True if the file existed and was deleted.
        """
        path = self._dir / f"{assembly_id}.json"
        if path.exists():
            path.unlink()
            logger.info("Deleted overrides for %s", assembly_id)
            return True
        return False

    # -- capture ------------------------------------------------------------

    def capture_step_override(
        self,
        assembly_id: str,
        step: AssemblyStep,
        source: str = "user",
    ) -> None:
        """Capture a single step's current state as a persistent override.

        If an override with the same ``match_pattern`` and ``match_part_ids``
        already exists, it is updated in place (no duplicates).

        Args:
            assembly_id: Assembly this step belongs to.
            step: The step whose settings to capture.
            source: Who created this override — ``"user"`` or ``"ai"``.
        """
        existing = self.load(assembly_id)
        overrides_list = existing.overrides if existing else []

        new_override = StepOverride(
            match_pattern=step.name,
            match_part_ids=list(step.part_ids),
            handler=step.handler,
            primitive_type=step.primitive_type,
            primitive_params=step.primitive_params,
            policy_id=step.policy_id,
            success_criteria=step.success_criteria.model_dump(by_alias=True),
            max_retries=step.max_retries,
            source=source,
            created_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        _upsert(overrides_list, new_override)
        result = AssemblyOverrides(assembly_id=assembly_id, overrides=overrides_list)
        self.save(result)

    # -- application --------------------------------------------------------

    def apply_to_graph(
        self,
        graph: AssemblyGraph,
        overrides: AssemblyOverrides,
    ) -> int:
        """Apply overrides to an assembly graph.

        Matches overrides to steps using ``match_pattern`` (substring of
        ``step.name``) and ``match_part_ids`` (intersection with
        ``step.part_ids``). Applies all non-None fields from the override.

        AI overrides are applied first, then user overrides, so user values
        win on conflict.

        Args:
            graph: Assembly graph to modify (mutated in-place).
            overrides: Overrides to apply.

        Returns:
            Number of steps that were modified.
        """
        if not overrides.overrides:
            return 0

        # AI first, user last → user wins on conflict
        sorted_overrides = sorted(
            overrides.overrides,
            key=lambda o: 0 if o.source == "ai" else 1,
        )

        modified: set[str] = set()
        for override in sorted_overrides:
            for step in graph.steps.values():
                if _matches(override, step):
                    _apply_override(step, override)
                    modified.add(step.id)

        return len(modified)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _matches(override: StepOverride, step: AssemblyStep) -> bool:
    """Check whether an override matches a step.

    Args:
        override: The override with matching criteria.
        step: The step to test.

    Returns:
        True if the override should be applied to this step.
    """
    has_pattern = override.match_pattern is not None
    has_parts = bool(override.match_part_ids)

    if not has_pattern and not has_parts:
        return False

    pattern_ok = override.match_pattern.lower() in step.name.lower() if has_pattern else True
    parts_ok = bool(set(override.match_part_ids) & set(step.part_ids)) if has_parts else True

    if has_pattern and has_parts:
        return pattern_ok and parts_ok
    if has_pattern:
        return pattern_ok
    return parts_ok


def _apply_override(step: AssemblyStep, override: StepOverride) -> None:
    """Apply a single override's non-None fields to a step.

    For ``primitive_params``, values are merged (override takes precedence
    but existing keys not in the override are preserved).

    Args:
        step: Step to mutate.
        override: Override whose non-None fields to apply.
    """
    if override.handler is not None:
        step.handler = override.handler
    if override.primitive_type is not None:
        step.primitive_type = override.primitive_type
    if override.primitive_params is not None:
        step.primitive_params = {**(step.primitive_params or {}), **override.primitive_params}
    if override.success_criteria is not None:
        step.success_criteria = SuccessCriteria.model_validate(override.success_criteria)
    if override.max_retries is not None:
        step.max_retries = override.max_retries
    if override.policy_id is not None:
        step.policy_id = override.policy_id


def _upsert(overrides: list[StepOverride], new: StepOverride) -> None:
    """Insert or update an override in a list, preventing duplicates.

    Two overrides are considered duplicates if they have the same
    ``match_pattern`` and ``match_part_ids`` (sorted for comparison).

    Args:
        overrides: Mutable list to update.
        new: Override to insert or replace.
    """
    new_parts = sorted(new.match_part_ids)
    for i, existing in enumerate(overrides):
        if (
            existing.match_pattern == new.match_pattern
            and sorted(existing.match_part_ids) == new_parts
        ):
            overrides[i] = new
            return
    overrides.append(new)
