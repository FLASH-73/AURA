"""Tests for nextis.assembly.ai_planner."""

from __future__ import annotations

import pytest

from nextis.assembly.ai_planner import AIPlanner, _spatial_summary
from nextis.assembly.models import (
    AssemblyGraph,
    AssemblyStep,
    ContactInfo,
    ContactType,
    Part,
    SuccessCriteria,
)
from nextis.errors import PlannerError


def _make_graph(
    *,
    contacts: list[ContactInfo] | None = None,
    parts: dict[str, Part] | None = None,
    steps: dict[str, AssemblyStep] | None = None,
    step_order: list[str] | None = None,
) -> AssemblyGraph:
    """Build a minimal AssemblyGraph for testing."""
    default_parts = {
        "shaft_01": Part(
            id="shaft_01",
            geometry="cylinder",
            dimensions=[0.015, 0.10],
            position=[0.0, 0.05, 0.0],
            shape_class="shaft",
        ),
        "housing_01": Part(
            id="housing_01",
            geometry="box",
            dimensions=[0.08, 0.04, 0.06],
            position=[0.0, 0.02, 0.0],
            shape_class="housing",
        ),
    }
    default_steps = {
        "step_001": AssemblyStep(
            id="step_001",
            name="Place housing",
            part_ids=["housing_01"],
            handler="primitive",
            primitive_type="place",
            primitive_params={"target_pose": [0.0, 0.02, 0.0]},
            success_criteria=SuccessCriteria(type="position"),
        ),
        "step_002": AssemblyStep(
            id="step_002",
            name="Insert shaft into housing",
            part_ids=["shaft_01"],
            dependencies=["step_001"],
            handler="policy",
            success_criteria=SuccessCriteria(type="classifier"),
        ),
    }
    return AssemblyGraph(
        id="test_asm",
        name="Test Assembly",
        parts=parts if parts is not None else default_parts,
        steps=steps if steps is not None else default_steps,
        step_order=step_order if step_order is not None else ["step_001", "step_002"],
        contacts=contacts or [],
    )


# ---------------------------------------------------------------------------
# Spatial summary — contact details
# ---------------------------------------------------------------------------


class TestSpatialSummaryContacts:
    """Tests for contact details in the spatial summary."""

    def test_includes_contact_details_section(self) -> None:
        """Graph with ContactInfo entries produces a 'Contact Details' heading."""
        contacts = [
            ContactInfo(
                part_a="housing_01",
                part_b="shaft_01",
                contact_type=ContactType.COAXIAL,
                clearance_mm=0.3,
                insertion_axis=[0.0, -1.0, 0.0],
            ),
        ]
        graph = _make_graph(contacts=contacts)
        summary = _spatial_summary(graph)
        assert "## Contact Details" in summary

    def test_coaxial_shows_clearance_and_axis(self) -> None:
        """Coaxial contact renders clearance and insertion axis."""
        contacts = [
            ContactInfo(
                part_a="housing_01",
                part_b="shaft_01",
                contact_type=ContactType.COAXIAL,
                clearance_mm=0.3,
                insertion_axis=[0.0, -1.0, 0.0],
            ),
        ]
        graph = _make_graph(contacts=contacts)
        summary = _spatial_summary(graph)
        assert "clearance 0.3mm" in summary
        assert "insertion axis [0.00, -1.00, 0.00]" in summary

    def test_planar_contact_shows_type(self) -> None:
        """Planar contact renders contact type and area class."""
        contacts = [
            ContactInfo(
                part_a="housing_01",
                part_b="shaft_01",
                contact_type=ContactType.PLANAR,
                area_class="large",
            ),
        ]
        graph = _make_graph(contacts=contacts)
        summary = _spatial_summary(graph)
        assert "planar" in summary
        assert "large contact area" in summary

    def test_no_contacts_omits_section(self) -> None:
        """Graph with empty contacts list omits 'Contact Details' section."""
        graph = _make_graph(contacts=[])
        summary = _spatial_summary(graph)
        assert "## Contact Details" not in summary


# ---------------------------------------------------------------------------
# Spatial summary — shape class column
# ---------------------------------------------------------------------------


class TestSpatialSummaryShapeClass:
    """Tests for shape_class column in the Part Catalog table."""

    def test_includes_shape_class_column(self) -> None:
        """Part Catalog table header includes 'Shape Class'."""
        graph = _make_graph()
        summary = _spatial_summary(graph)
        assert "Shape Class" in summary

    def test_shows_shape_class_values(self) -> None:
        """Parts with shape_class show values in the table."""
        graph = _make_graph()
        summary = _spatial_summary(graph)
        assert "shaft" in summary
        assert "housing" in summary

    def test_missing_shape_class_shows_dash(self) -> None:
        """Parts without shape_class show '-' in the column."""
        parts = {
            "plain_part": Part(
                id="plain_part",
                geometry="box",
                dimensions=[0.05, 0.05, 0.05],
                position=[0.0, 0.0, 0.0],
            ),
        }
        graph = _make_graph(parts=parts, steps={}, step_order=[])
        summary = _spatial_summary(graph)
        # The shape_class column should show "-" for parts without one
        lines = summary.split("\n")
        part_line = next(line for line in lines if "plain_part" in line)
        # Table columns: ID | Geometry | Shape Class | Dimensions | Position | Volume
        cols = [c.strip() for c in part_line.split("|")]
        # cols[0] is empty (before first |), cols[1]=ID, cols[2]=Geometry, cols[3]=ShapeClass
        assert cols[3] == "-"


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------


class TestParseResponse:
    """Tests for AIPlanner._parse_response()."""

    def test_malformed_json_raises(self) -> None:
        """Garbage input raises PlannerError."""
        planner = AIPlanner(api_key="test-key")
        with pytest.raises(PlannerError, match="invalid JSON"):
            planner._parse_response("this is not json {{{")

    def test_valid_json_parses(self) -> None:
        """Well-formed JSON produces correct PlanAnalysis."""
        planner = AIPlanner(api_key="test-key")
        raw = """{
            "suggestions": [
                {
                    "stepId": "step_001",
                    "field": "handler",
                    "oldValue": "primitive",
                    "newValue": "policy",
                    "reason": "tight clearance"
                }
            ],
            "warnings": ["gear meshing detected"],
            "difficultyScore": 7,
            "estimatedTeachingMinutes": 15,
            "summary": "Moderate difficulty assembly."
        }"""
        analysis = planner._parse_response(raw)
        assert len(analysis.suggestions) == 1
        assert analysis.suggestions[0].step_id == "step_001"
        assert analysis.suggestions[0].field == "handler"
        assert analysis.warnings == ["gear meshing detected"]
        assert analysis.difficulty_score == 7
        assert analysis.estimated_teaching_minutes == 15
        assert "Moderate" in analysis.summary

    def test_strips_markdown_fences(self) -> None:
        """Markdown-fenced JSON is parsed correctly."""
        planner = AIPlanner(api_key="test-key")
        raw = '```json\n{"suggestions": [], "warnings": [], "difficultyScore": 3}\n```'
        analysis = planner._parse_response(raw)
        assert analysis.suggestions == []
        assert analysis.difficulty_score == 3

    def test_difficulty_score_clamped(self) -> None:
        """Difficulty score is clamped to [1, 10]."""
        planner = AIPlanner(api_key="test-key")
        raw = '{"suggestions": [], "difficultyScore": 99}'
        analysis = planner._parse_response(raw)
        assert analysis.difficulty_score == 10


# ---------------------------------------------------------------------------
# _apply_suggestions validation
# ---------------------------------------------------------------------------


class TestApplySuggestions:
    """Tests for _apply_suggestions() validation logic."""

    def test_unknown_primitive_type_rejected(self) -> None:
        """Suggestion with invalid primitive_type is skipped."""
        from nextis.api.routes.assembly import _apply_suggestions
        from nextis.assembly.ai_planner import PlanSuggestion

        graph = _make_graph()
        suggestions = [
            PlanSuggestion(
                step_id="step_001",
                field="primitiveType",
                old_value="place",
                new_value="nonexistent_primitive",
                reason="test",
            ),
        ]
        _apply_suggestions(graph, suggestions)
        # Should remain unchanged
        assert graph.steps["step_001"].primitive_type == "place"

    def test_valid_primitive_type_applied(self) -> None:
        """Suggestion with valid primitive_type is applied."""
        from nextis.api.routes.assembly import _apply_suggestions
        from nextis.assembly.ai_planner import PlanSuggestion

        graph = _make_graph()
        suggestions = [
            PlanSuggestion(
                step_id="step_001",
                field="primitiveType",
                old_value="place",
                new_value="press_fit",
                reason="test",
            ),
        ]
        _apply_suggestions(graph, suggestions)
        assert graph.steps["step_001"].primitive_type == "press_fit"
