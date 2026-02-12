"""Shared test fixtures for the Nextis Assembler test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nextis.assembly.models import AssemblyGraph

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "configs" / "assemblies"


def _primitives_only_assembly_data() -> dict:
    """A 3-step primitive-only assembly for fast, non-blocking tests."""
    return {
        "id": "test_assembly",
        "name": "Test Assembly",
        "parts": {
            "part_a": {
                "id": "part_a",
                "cadFile": None,
                "meshFile": None,
                "graspPoints": [],
                "position": [0, 0, 0],
                "geometry": "box",
                "dimensions": [0.05, 0.05, 0.05],
                "color": "#AAAAAA",
            },
        },
        "steps": {
            "step_001": {
                "id": "step_001",
                "name": "Pick part A",
                "partIds": ["part_a"],
                "dependencies": [],
                "handler": "primitive",
                "primitiveType": "pick",
                "primitiveParams": {"grasp_pose": [0, 0, 0, 0, 0, 0]},
                "policyId": None,
                "successCriteria": {"type": "force_threshold", "threshold": 0.5},
                "maxRetries": 1,
            },
            "step_002": {
                "id": "step_002",
                "name": "Place part A",
                "partIds": ["part_a"],
                "dependencies": ["step_001"],
                "handler": "primitive",
                "primitiveType": "place",
                "primitiveParams": {"target_pose": [0.1, 0, 0]},
                "policyId": None,
                "successCriteria": {"type": "position"},
                "maxRetries": 1,
            },
            "step_003": {
                "id": "step_003",
                "name": "Press fit part A",
                "partIds": ["part_a"],
                "dependencies": ["step_002"],
                "handler": "primitive",
                "primitiveType": "press_fit",
                "primitiveParams": {"direction": [0, -1, 0], "force_target": 10},
                "policyId": None,
                "successCriteria": {"type": "force_threshold", "threshold": 10},
                "maxRetries": 1,
            },
        },
        "stepOrder": ["step_001", "step_002", "step_003"],
    }


@pytest.fixture()
def primitives_only_graph(tmp_path: Path) -> AssemblyGraph:
    """Write a 3-step primitive-only assembly to tmp_path and return loaded graph."""
    data = _primitives_only_assembly_data()
    path = tmp_path / "test_assembly.json"
    path.write_text(json.dumps(data, indent=2))
    return AssemblyGraph.from_json_file(path)


@pytest.fixture()
def bearing_housing_graph() -> AssemblyGraph:
    """Load the real bearing_housing_v1 fixture (has a policy step)."""
    return AssemblyGraph.from_json_file(FIXTURE_DIR / "bearing_housing_v1.json")


@pytest.fixture()
def analytics_dir(tmp_path: Path) -> Path:
    """Return a clean temporary directory for analytics data."""
    d = tmp_path / "analytics"
    d.mkdir()
    return d
