"""Integration tests for the FastAPI routes.

Uses monkeypatching to redirect CONFIGS_DIR and ANALYTICS_DIR to tmp_path,
isolating each test from real data on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _test_assembly_data() -> dict:
    """A 2-step primitive-only assembly for API tests."""
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
        },
        "stepOrder": ["step_001", "step_002"],
    }


@pytest.fixture()
def isolated_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create an isolated FastAPI TestClient with tmp_path for all data dirs."""
    configs_dir = tmp_path / "configs" / "assemblies"
    configs_dir.mkdir(parents=True)
    analytics_dir = tmp_path / "data" / "analytics"
    analytics_dir.mkdir(parents=True)

    # Write fixture assembly
    (configs_dir / "test_assembly.json").write_text(json.dumps(_test_assembly_data(), indent=2))

    # Monkeypatch route-module directory constants
    import nextis.api.routes.analytics as analytics_mod
    import nextis.api.routes.assembly as asm_mod
    import nextis.api.routes.execution as exec_mod

    monkeypatch.setattr(asm_mod, "CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(exec_mod, "CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(exec_mod, "ANALYTICS_DIR", analytics_dir)
    monkeypatch.setattr(analytics_mod, "CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(analytics_mod, "ANALYTICS_DIR", analytics_dir)

    # Reset module-level sequencer state
    monkeypatch.setattr(exec_mod, "_sequencer", None)
    monkeypatch.setattr(exec_mod, "_analytics_store", None)

    from nextis.api.app import app

    return TestClient(app)


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------


def test_health(isolated_app: TestClient) -> None:
    r = isolated_app.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ------------------------------------------------------------------
# Assembly routes
# ------------------------------------------------------------------


def test_list_assemblies(isolated_app: TestClient) -> None:
    r = isolated_app.get("/assemblies")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    ids = [a["id"] for a in data]
    assert "test_assembly" in ids


def test_get_assembly(isolated_app: TestClient) -> None:
    r = isolated_app.get("/assemblies/test_assembly")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "test_assembly"
    assert "parts" in data
    assert "steps" in data
    assert "stepOrder" in data
    assert len(data["stepOrder"]) == 2


def test_create_assembly(isolated_app: TestClient) -> None:
    new_graph = {
        "id": "new_assembly",
        "name": "New Assembly",
        "parts": {},
        "steps": {
            "step_001": {
                "id": "step_001",
                "name": "Do something",
                "partIds": [],
                "dependencies": [],
                "handler": "primitive",
                "primitiveType": "move_to",
                "primitiveParams": {"target_pose": [0, 0, 0]},
                "policyId": None,
                "successCriteria": {"type": "position"},
                "maxRetries": 1,
            },
        },
        "stepOrder": ["step_001"],
    }
    r = isolated_app.post("/assemblies", json=new_graph)
    assert r.status_code == 201

    # Verify it appears in the list
    r2 = isolated_app.get("/assemblies")
    ids = [a["id"] for a in r2.json()]
    assert "new_assembly" in ids


def test_update_step(isolated_app: TestClient) -> None:
    r = isolated_app.patch(
        "/assemblies/test_assembly/steps/step_001",
        json={"name": "Updated pick"},
    )
    assert r.status_code == 200

    # Verify the update persisted
    r2 = isolated_app.get("/assemblies/test_assembly")
    step = r2.json()["steps"]["step_001"]
    assert step["name"] == "Updated pick"


def test_404_missing_assembly(isolated_app: TestClient) -> None:
    r = isolated_app.get("/assemblies/nonexistent")
    assert r.status_code == 404


# ------------------------------------------------------------------
# Execution routes
# ------------------------------------------------------------------


def test_start_execution(isolated_app: TestClient) -> None:
    r = isolated_app.post("/execution/start", json={"assemblyId": "test_assembly"})
    assert r.status_code == 200

    # Check that state reflects running (or already complete — stubs are fast)
    r2 = isolated_app.get("/execution/state")
    assert r2.json()["phase"] in ("running", "complete")
    assert r2.json()["assemblyId"] == "test_assembly"
