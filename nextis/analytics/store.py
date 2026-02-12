"""Filesystem-backed analytics store for per-step execution metrics.

Stores run data as JSON files under {root}/{assembly_id}.json.
Each file maps step IDs to a list of run entries. The store computes
aggregated metrics (success rate, average duration, etc.) on the fly.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

from nextis.api.schemas import RunEntry, StepMetrics

logger = logging.getLogger(__name__)

# Maximum runs stored per step to prevent unbounded file growth.
_MAX_STORED_RUNS = 200


class AnalyticsStore:
    """Per-step analytics persistence backed by JSON files.

    Thread-safe via a lock. One JSON file per assembly at
    ``{root}/{assembly_id}.json``.

    Args:
        root: Base directory for analytics data. Created on first write.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._lock = threading.Lock()

    def record_step_result(
        self,
        assembly_id: str,
        step_id: str,
        *,
        success: bool,
        duration_ms: float,
        attempt: int = 1,
    ) -> None:
        """Append a step result to the assembly's analytics file.

        Args:
            assembly_id: Assembly this run belongs to.
            step_id: Step within the assembly.
            success: Whether the attempt succeeded.
            duration_ms: Execution time in milliseconds.
            attempt: Which attempt number (1-indexed).
        """
        entry = {
            "success": success,
            "durationMs": duration_ms,
            "timestamp": time.time(),
            "attempt": attempt,
        }

        with self._lock:
            path = self._assembly_path(assembly_id)
            data = self._load(path)

            if step_id not in data:
                data[step_id] = {"runs": []}

            runs = data[step_id]["runs"]
            runs.append(entry)

            # Trim to cap
            if len(runs) > _MAX_STORED_RUNS:
                data[step_id]["runs"] = runs[-_MAX_STORED_RUNS:]

            self._save(path, data)

        logger.debug(
            "Recorded run: assembly=%s step=%s success=%s duration=%.0fms",
            assembly_id,
            step_id,
            success,
            duration_ms,
        )

    def get_step_metrics(self, assembly_id: str) -> list[StepMetrics]:
        """Compute aggregated metrics for all steps in an assembly.

        Args:
            assembly_id: Assembly identifier.

        Returns:
            List of StepMetrics for every step that has recorded data.
        """
        path = self._assembly_path(assembly_id)
        data = self._load(path)

        metrics: list[StepMetrics] = []
        for step_id, step_data in data.items():
            metrics.append(self._compute_metrics(step_id, step_data.get("runs", [])))
        return metrics

    def get_step_metrics_for(
        self,
        assembly_id: str,
        step_ids: list[str],
    ) -> list[StepMetrics]:
        """Compute metrics for specific steps, returning zeros for steps with no data.

        Args:
            assembly_id: Assembly identifier.
            step_ids: Step IDs to compute metrics for.

        Returns:
            List of StepMetrics, one per step_id, in order.
        """
        path = self._assembly_path(assembly_id)
        data = self._load(path)

        return [self._compute_metrics(sid, data.get(sid, {}).get("runs", [])) for sid in step_ids]

    def get_step_history(
        self,
        assembly_id: str,
        step_id: str,
        limit: int = 50,
    ) -> list[RunEntry]:
        """Get recent run history for a single step.

        Args:
            assembly_id: Assembly identifier.
            step_id: Step identifier.
            limit: Maximum entries to return (most recent first).

        Returns:
            List of RunEntry, most recent last.
        """
        path = self._assembly_path(assembly_id)
        data = self._load(path)
        runs = data.get(step_id, {}).get("runs", [])

        return [
            RunEntry(
                success=r["success"],
                duration_ms=r["durationMs"],
                timestamp=r["timestamp"],
            )
            for r in runs[-limit:]
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assembly_path(self, assembly_id: str) -> Path:
        return self._root / f"{assembly_id}.json"

    def _load(self, path: Path) -> dict:
        """Load analytics JSON, returning empty dict if missing or corrupt."""
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, KeyError):
                logger.warning("Corrupt analytics file %s, resetting", path)
        return {}

    def _save(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")

    @staticmethod
    def _compute_metrics(step_id: str, runs: list[dict]) -> StepMetrics:
        """Compute aggregated metrics from a list of raw run dicts."""
        total = len(runs)
        successes = sum(1 for r in runs if r["success"])
        success_rate = successes / total if total > 0 else 0.0

        durations = [r["durationMs"] for r in runs if r["success"]]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        recent = [
            RunEntry(
                success=r["success"],
                duration_ms=r["durationMs"],
                timestamp=r["timestamp"],
            )
            for r in runs[-20:]
        ]

        return StepMetrics(
            step_id=step_id,
            success_rate=round(success_rate, 4),
            avg_duration_ms=round(avg_duration, 1),
            total_attempts=total,
            demo_count=0,
            recent_runs=recent,
        )
