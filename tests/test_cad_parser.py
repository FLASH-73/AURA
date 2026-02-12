"""Tests for the CAD parser and sequence planner.

Requires OCP (pip: cadquery-ocp) or pythonocc-core (conda).
All tests are skipped automatically when neither is available.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Guard: skip all tests if no OpenCASCADE bindings installed
_occ_available = True
try:
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
except ImportError:
    try:
        from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
        from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
    except ImportError:
        _occ_available = False

pytestmark = pytest.mark.skipif(not _occ_available, reason="OCP/pythonocc-core not installed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def step_file_3parts(tmp_path: Path) -> Path:
    """Create a STEP file with a box + two cylinders.

    Layout (in metres):
    - Housing: 80x40x60mm box centred at origin
    - Bearing: cylinder r=15mm h=10mm, sitting on top of housing
    - Pin: small cylinder r=3mm h=15mm, inside the housing
    """
    writer = STEPControl_Writer()

    # Housing (box)
    housing = BRepPrimAPI_MakeBox(gp_Pnt(-0.04, 0, -0.03), 0.08, 0.04, 0.06).Shape()
    writer.Transfer(housing, STEPControl_AsIs)

    # Bearing (cylinder on top face of housing)
    ax_bearing = gp_Ax2(gp_Pnt(0, 0.04, 0), gp_Dir(0, 1, 0))
    bearing = BRepPrimAPI_MakeCylinder(ax_bearing, 0.015, 0.01).Shape()
    writer.Transfer(bearing, STEPControl_AsIs)

    # Pin (small cylinder)
    ax_pin = gp_Ax2(gp_Pnt(-0.025, 0.01, 0), gp_Dir(0, 1, 0))
    pin = BRepPrimAPI_MakeCylinder(ax_pin, 0.003, 0.015).Shape()
    writer.Transfer(pin, STEPControl_AsIs)

    step_path = tmp_path / "test_assembly.step"
    status = writer.Write(str(step_path))
    assert status == IFSelect_RetDone, "Failed to write test STEP file"
    return step_path


@pytest.fixture()
def step_file_single_box(tmp_path: Path) -> Path:
    """Create a STEP file with a single box (no assembly structure)."""
    writer = STEPControl_Writer()
    box = BRepPrimAPI_MakeBox(0.1, 0.05, 0.03).Shape()
    writer.Transfer(box, STEPControl_AsIs)
    path = tmp_path / "single_box.step"
    status = writer.Write(str(path))
    assert status == IFSelect_RetDone
    return path


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------
class TestCADParser:
    """Tests for CADParser.parse()."""

    def test_parse_extracts_correct_part_count(self, step_file_3parts: Path, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser

        parser = CADParser()
        result = parser.parse(step_file_3parts, tmp_path / "meshes")
        assert len(result.graph.parts) == 3

    def test_parse_generates_glb_files(self, step_file_3parts: Path, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser

        mesh_dir = tmp_path / "meshes"
        parser = CADParser()
        parser.parse(step_file_3parts, mesh_dir)

        glb_files = list(mesh_dir.glob("*.glb"))
        assert len(glb_files) >= 1, f"Expected GLB files, found: {glb_files}"

    def test_parse_assigns_position_and_geometry(self, step_file_3parts: Path, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser

        parser = CADParser()
        result = parser.parse(step_file_3parts, tmp_path / "meshes")

        for part in result.graph.parts.values():
            assert part.position is not None, f"{part.id} missing position"
            assert len(part.position) == 3
            assert part.geometry in {"box", "cylinder", "sphere"}, f"{part.id}: {part.geometry}"
            assert part.dimensions is not None and len(part.dimensions) >= 1
            assert part.color is not None and part.color.startswith("#")

    def test_parse_assigns_mesh_file_paths(self, step_file_3parts: Path, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser

        parser = CADParser()
        result = parser.parse(step_file_3parts, tmp_path / "meshes")

        parts_with_mesh = [p for p in result.graph.parts.values() if p.mesh_file]
        assert len(parts_with_mesh) >= 1, "Expected at least one part with mesh_file"
        for part in parts_with_mesh:
            assert part.mesh_file.endswith(".glb")

    def test_parse_single_part(self, step_file_single_box: Path, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser

        parser = CADParser()
        result = parser.parse(step_file_single_box, tmp_path / "meshes")
        assert len(result.graph.parts) == 1
        assert result.contacts == []

    def test_parse_nonexistent_file_raises(self, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser

        parser = CADParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(tmp_path / "no_such_file.step", tmp_path / "meshes")

    def test_parse_invalid_suffix_raises(self, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser
        from nextis.errors import CADParseError

        bad_file = tmp_path / "readme.txt"
        bad_file.write_text("not a step file")
        parser = CADParser()
        with pytest.raises(CADParseError, match="Expected .step/.stp"):
            parser.parse(bad_file, tmp_path / "meshes")

    def test_assembly_graph_round_trip(self, step_file_3parts: Path, tmp_path: Path):
        """Graph from parser survives JSON serialize/deserialize."""
        from nextis.assembly.cad_parser import CADParser
        from nextis.assembly.models import AssemblyGraph

        parser = CADParser()
        result = parser.parse(step_file_3parts, tmp_path / "meshes")
        graph = result.graph

        json_path = tmp_path / "test_graph.json"
        graph.to_json_file(json_path)
        loaded = AssemblyGraph.from_json_file(json_path)

        assert loaded.id == graph.id
        assert len(loaded.parts) == len(graph.parts)
        for part_id in graph.parts:
            assert part_id in loaded.parts


# ---------------------------------------------------------------------------
# Geometry classification tests
# ---------------------------------------------------------------------------
class TestClassifyGeometry:
    """Tests for the classify_geometry helper."""

    def test_box(self):
        from nextis.assembly.mesh_utils import classify_geometry

        geo, dims = classify_geometry(0.08, 0.04, 0.06)
        assert geo == "box"
        assert dims == [0.08, 0.04, 0.06]

    def test_cylinder(self):
        from nextis.assembly.mesh_utils import classify_geometry

        geo, _dims = classify_geometry(0.03, 0.1, 0.03)
        assert geo == "cylinder"

    def test_sphere(self):
        from nextis.assembly.mesh_utils import classify_geometry

        geo, _dims = classify_geometry(0.05, 0.05, 0.048)
        assert geo == "sphere"

    def test_flat_box(self):
        from nextis.assembly.mesh_utils import classify_geometry

        geo, dims = classify_geometry(0.1, 0.01, 0.1)
        assert geo == "box"
        assert len(dims) == 3


# ---------------------------------------------------------------------------
# Sequence planner tests
# ---------------------------------------------------------------------------
class TestSequencePlanner:
    """Tests for SequencePlanner.plan()."""

    def test_generates_steps(self, step_file_3parts: Path, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser
        from nextis.assembly.sequence_planner import SequencePlanner

        parser = CADParser()
        result = parser.parse(step_file_3parts, tmp_path / "meshes")

        planner = SequencePlanner()
        graph = planner.plan(result)

        assert len(graph.steps) > 0
        assert len(graph.step_order) == len(graph.steps)

    def test_step_order_ids_exist_in_steps(self, step_file_3parts: Path, tmp_path: Path):
        from nextis.assembly.cad_parser import CADParser
        from nextis.assembly.sequence_planner import SequencePlanner

        parser = CADParser()
        result = parser.parse(step_file_3parts, tmp_path / "meshes")
        graph = SequencePlanner().plan(result)

        for step_id in graph.step_order:
            assert step_id in graph.steps, f"{step_id} not in steps dict"

    def test_dependencies_respected(self, step_file_3parts: Path, tmp_path: Path):
        """All dependencies appear before their dependent step in step_order."""
        from nextis.assembly.cad_parser import CADParser
        from nextis.assembly.sequence_planner import SequencePlanner

        parser = CADParser()
        result = parser.parse(step_file_3parts, tmp_path / "meshes")
        graph = SequencePlanner().plan(result)

        order_index = {sid: i for i, sid in enumerate(graph.step_order)}
        for step_id, step in graph.steps.items():
            for dep in step.dependencies:
                assert order_index[dep] < order_index[step_id], (
                    f"Dependency {dep} should come before {step_id}"
                )

    def test_empty_parts_raises(self):
        from nextis.assembly.cad_parser import ParseResult
        from nextis.assembly.models import AssemblyGraph
        from nextis.assembly.sequence_planner import SequencePlanner
        from nextis.errors import AssemblyError

        empty = ParseResult(
            graph=AssemblyGraph(id="empty", name="Empty"),
            contacts=[],
        )
        with pytest.raises(AssemblyError, match="no parts"):
            SequencePlanner().plan(empty)

    def test_full_pipeline_round_trip(self, step_file_3parts: Path, tmp_path: Path):
        """Full pipeline: parse → plan → serialize → deserialize."""
        from nextis.assembly.cad_parser import CADParser
        from nextis.assembly.models import AssemblyGraph
        from nextis.assembly.sequence_planner import SequencePlanner

        parser = CADParser()
        result = parser.parse(step_file_3parts, tmp_path / "meshes")
        graph = SequencePlanner().plan(result)

        json_path = tmp_path / "full_pipeline.json"
        graph.to_json_file(json_path)
        loaded = AssemblyGraph.from_json_file(json_path)

        assert loaded.id == graph.id
        assert len(loaded.steps) == len(graph.steps)
        assert loaded.step_order == graph.step_order
