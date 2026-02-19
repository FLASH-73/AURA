"""Tests for the assembly override persistence system."""

from __future__ import annotations

import json
from pathlib import Path

from nextis.assembly.models import AssemblyGraph, AssemblyStep, SuccessCriteria
from nextis.assembly.overrides import (
    AssemblyOverrides,
    OverrideStore,
    StepOverride,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph(
    assembly_id: str = "test_asm",
    steps: dict[str, AssemblyStep] | None = None,
) -> AssemblyGraph:
    """Build a minimal assembly graph for testing."""
    if steps is None:
        steps = {
            "step_001": AssemblyStep(
                id="step_001",
                name="Pick gear_sun",
                part_ids=["gear_sun"],
                handler="primitive",
                primitive_type="pick",
                primitive_params={"part_id": "gear_sun", "approach_height": 0.05},
                success_criteria=SuccessCriteria(type="force_threshold", threshold=0.5),
            ),
            "step_002": AssemblyStep(
                id="step_002",
                name="Assemble gear_sun onto shaft",
                part_ids=["gear_sun", "shaft"],
                handler="primitive",
                primitive_type="place",
                primitive_params={"part_id": "gear_sun", "target_pose": [0.1, 0, 0]},
            ),
            "step_003": AssemblyStep(
                id="step_003",
                name="Insert bearing into housing",
                part_ids=["bearing", "housing"],
                handler="primitive",
                primitive_type="linear_insert",
                primitive_params={"part_id": "bearing", "force_limit": 10.0},
            ),
        }
    return AssemblyGraph(
        id=assembly_id,
        name="Test Assembly",
        steps=steps,
        step_order=list(steps.keys()),
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Save overrides, load them back, verify equality."""
    store = OverrideStore(base_dir=tmp_path)
    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(
                match_pattern="Pick gear_sun",
                match_part_ids=["gear_sun"],
                handler="policy",
                policy_id="checkpoints/gear_sun.pt",
                source="user",
                created_at="2026-02-19T10:00:00",
            ),
        ],
    )
    store.save(overrides)

    loaded = store.load("test_asm")
    assert loaded is not None
    assert len(loaded.overrides) == 1
    ov = loaded.overrides[0]
    assert ov.match_pattern == "Pick gear_sun"
    assert ov.match_part_ids == ["gear_sun"]
    assert ov.handler == "policy"
    assert ov.policy_id == "checkpoints/gear_sun.pt"
    assert ov.source == "user"
    assert ov.created_at == "2026-02-19T10:00:00"


def test_load_missing_returns_none(tmp_path: Path) -> None:
    """Loading overrides for a non-existent assembly returns None."""
    store = OverrideStore(base_dir=tmp_path)
    assert store.load("nonexistent") is None


def test_apply_by_part_id(tmp_path: Path) -> None:
    """Override with match_part_ids modifies the correct step."""
    store = OverrideStore(base_dir=tmp_path)
    graph = _make_graph()

    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(
                match_part_ids=["gear_sun"],
                handler="policy",
                max_retries=5,
            ),
        ],
    )

    count = store.apply_to_graph(graph, overrides)

    # Should match step_001 (Pick gear_sun) and step_002 (Assemble gear_sun onto shaft)
    assert count == 2
    assert graph.steps["step_001"].handler == "policy"
    assert graph.steps["step_001"].max_retries == 5
    assert graph.steps["step_002"].handler == "policy"
    # step_003 should be untouched
    assert graph.steps["step_003"].handler == "primitive"
    assert graph.steps["step_003"].max_retries == 3


def test_apply_by_name_pattern(tmp_path: Path) -> None:
    """Override with match_pattern matches steps containing the substring."""
    store = OverrideStore(base_dir=tmp_path)
    graph = _make_graph()

    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(
                match_pattern="Assemble gear",
                handler="policy",
            ),
        ],
    )

    count = store.apply_to_graph(graph, overrides)

    assert count == 1
    assert graph.steps["step_002"].handler == "policy"
    # Other steps untouched
    assert graph.steps["step_001"].handler == "primitive"
    assert graph.steps["step_003"].handler == "primitive"


def test_apply_name_pattern_case_insensitive(tmp_path: Path) -> None:
    """Name pattern matching is case-insensitive."""
    store = OverrideStore(base_dir=tmp_path)
    graph = _make_graph()

    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(match_pattern="INSERT BEARING", handler="policy"),
        ],
    )

    count = store.apply_to_graph(graph, overrides)
    assert count == 1
    assert graph.steps["step_003"].handler == "policy"


def test_primitive_params_merge(tmp_path: Path) -> None:
    """Override params are merged with existing (not replaced)."""
    store = OverrideStore(base_dir=tmp_path)
    graph = _make_graph()

    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(
                match_part_ids=["bearing"],
                primitive_params={"force_limit": 25.0, "compliance_axes": [1, 1, 0, 0, 0, 0]},
            ),
        ],
    )

    count = store.apply_to_graph(graph, overrides)
    assert count == 1
    params = graph.steps["step_003"].primitive_params
    assert params is not None
    # Original key preserved
    assert params["part_id"] == "bearing"
    # Overridden value
    assert params["force_limit"] == 25.0
    # New key added
    assert params["compliance_axes"] == [1, 1, 0, 0, 0, 0]


def test_user_overrides_win(tmp_path: Path) -> None:
    """User overrides beat AI overrides when both match the same step."""
    store = OverrideStore(base_dir=tmp_path)
    graph = _make_graph()

    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(
                match_part_ids=["bearing"],
                max_retries=5,
                source="ai",
            ),
            StepOverride(
                match_part_ids=["bearing"],
                max_retries=2,
                source="user",
            ),
        ],
    )

    store.apply_to_graph(graph, overrides)
    # User override applied last → user wins
    assert graph.steps["step_003"].max_retries == 2


def test_no_overrides_no_changes(tmp_path: Path) -> None:
    """Applying empty overrides doesn't modify the graph."""
    store = OverrideStore(base_dir=tmp_path)
    graph = _make_graph()

    # Snapshot original state
    original = graph.model_dump()

    overrides = AssemblyOverrides(assembly_id="test_asm", overrides=[])
    count = store.apply_to_graph(graph, overrides)

    assert count == 0
    assert graph.model_dump() == original


def test_duplicate_prevention(tmp_path: Path) -> None:
    """Capturing the same override twice doesn't create duplicates."""
    store = OverrideStore(base_dir=tmp_path)
    step = AssemblyStep(
        id="step_001",
        name="Pick gear_sun",
        part_ids=["gear_sun"],
        handler="primitive",
        primitive_type="pick",
    )

    store.capture_step_override("test_asm", step, source="user")
    # Capture again with different handler
    step.handler = "policy"
    store.capture_step_override("test_asm", step, source="user")

    loaded = store.load("test_asm")
    assert loaded is not None
    assert len(loaded.overrides) == 1
    assert loaded.overrides[0].handler == "policy"


def test_delete_overrides(tmp_path: Path) -> None:
    """Delete removes the override file."""
    store = OverrideStore(base_dir=tmp_path)
    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[StepOverride(match_pattern="Pick", handler="policy")],
    )
    store.save(overrides)
    assert store.load("test_asm") is not None

    assert store.delete("test_asm") is True
    assert store.load("test_asm") is None
    assert store.delete("test_asm") is False


def test_both_criteria_must_match(tmp_path: Path) -> None:
    """When both match_pattern and match_part_ids are set, both must match."""
    store = OverrideStore(base_dir=tmp_path)
    graph = _make_graph()

    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(
                match_pattern="Assemble",
                match_part_ids=["housing"],
                handler="policy",
            ),
        ],
    )

    count = store.apply_to_graph(graph, overrides)
    # step_002 name matches "Assemble" but part_ids are [gear_sun, shaft] — no housing
    # step_003 has housing but name is "Insert bearing..." — no "Assemble"
    assert count == 0


def test_override_survives_reupload(tmp_path: Path) -> None:
    """Full integration: override persists across simulated re-upload.

    1. Build graph with default steps.
    2. Capture an override for one step.
    3. Build a fresh graph (simulating re-parse with new step IDs).
    4. Apply overrides to fresh graph.
    5. Verify the override took effect.
    """
    store = OverrideStore(base_dir=tmp_path)

    # Original graph — user changes step_002 handler to "policy"
    original = _make_graph()
    step = original.steps["step_002"]
    step.handler = "policy"
    step.policy_id = "models/gear_sun_v1.pt"
    store.capture_step_override("test_asm", step, source="user")

    # Simulate re-upload: fresh graph with different step IDs but same part names
    fresh_steps = {
        "step_010": AssemblyStep(
            id="step_010",
            name="Pick gear_sun",
            part_ids=["gear_sun"],
            handler="primitive",
            primitive_type="pick",
        ),
        "step_011": AssemblyStep(
            id="step_011",
            name="Assemble gear_sun onto shaft",
            part_ids=["gear_sun", "shaft"],
            handler="primitive",
            primitive_type="place",
        ),
    }
    fresh_graph = _make_graph(steps=fresh_steps)

    overrides = store.load("test_asm")
    assert overrides is not None
    count = store.apply_to_graph(fresh_graph, overrides)

    # The override targeted "Assemble gear_sun onto shaft" with part_ids [gear_sun, shaft]
    # It should match step_011 despite the different step ID
    assert count == 1
    assert fresh_graph.steps["step_011"].handler == "policy"
    assert fresh_graph.steps["step_011"].policy_id == "models/gear_sun_v1.pt"
    # step_010 should remain untouched
    assert fresh_graph.steps["step_010"].handler == "primitive"


def test_success_criteria_override(tmp_path: Path) -> None:
    """Success criteria can be overridden via dict."""
    store = OverrideStore(base_dir=tmp_path)
    graph = _make_graph()

    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(
                match_part_ids=["bearing"],
                success_criteria={"type": "classifier", "model": "bearing_check_v1"},
            ),
        ],
    )

    store.apply_to_graph(graph, overrides)
    sc = graph.steps["step_003"].success_criteria
    assert sc.type == "classifier"
    assert sc.model == "bearing_check_v1"


def test_json_camel_case_serialization(tmp_path: Path) -> None:
    """Override JSON uses camelCase keys."""
    store = OverrideStore(base_dir=tmp_path)
    overrides = AssemblyOverrides(
        assembly_id="test_asm",
        overrides=[
            StepOverride(
                match_pattern="Pick",
                match_part_ids=["shaft"],
                primitive_type="pick",
                primitive_params={"part_id": "shaft"},
                source="user",
                created_at="2026-01-01T00:00:00",
            ),
        ],
    )
    store.save(overrides)

    raw = json.loads((tmp_path / "test_asm.json").read_text())
    assert "assemblyId" in raw
    ov = raw["overrides"][0]
    assert "matchPattern" in ov
    assert "matchPartIds" in ov
    assert "primitiveType" in ov
    assert "primitiveParams" in ov
    assert "createdAt" in ov
