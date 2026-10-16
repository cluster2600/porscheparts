"""Check that the native analysis derivative preserves shared faces and rejects islands."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/962-cylinder-head-f0/source/flow4l"
spec = importlib.util.spec_from_file_location("flow4l_mesh", SOURCE / "build_flow_case.py")
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)
spec = importlib.util.spec_from_file_location("flow4l_mesh_gate", SOURCE / "accept_mesh.py")
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)


class Flow4LTests(unittest.TestCase):
    def test_connected_rectangular_channel_has_only_its_external_boundary(self):
        cells = [[i, j, k] for i in range(3) for j in range(2) for k in range(2)]
        nodes, hexes, faces = flow.topology(cells, [3, 2, 2])
        self.assertEqual(len(nodes), 36)
        self.assertEqual(len(hexes), 12)
        self.assertEqual({k: len(v) for k, v in faces.items()}, dict(inlet=4, outlet=4, walls=24))
        self.assertEqual(len(set(hexes[0]) & set(hexes[1])), 4)
        coords = {tag: p for p, tag in nodes.items()}
        self.assertTrue(all(coords[n][0] == 0 for face in faces["inlet"] for n in face))
        self.assertTrue(all(coords[n][0] == 3 for face in faces["outlet"] for n in face))

    def test_grid_does_not_silently_drop_isolated_or_duplicate_cells(self):
        for cells in ([[0, 0, 0], [2, 0, 0]], [[0, 0, 0], [0, 0, 0]],
                      [[True, 0, 0]], [[3, 0, 0]], []):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                flow.topology(cells, [3, 1, 1])

    def test_mesh_gate_rejects_bad_quality_before_any_result_can_be_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)
            (case / "log.checkMesh").write_text("cells: 1\nFailed 1 mesh checks.\nEnd\n")
            with self.assertRaises(ValueError): gate.accept(case)
            self.assertFalse((case / "mesh-report.json").exists())

    def test_mesh_gate_requires_wall_type_and_nonempty_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp); (case / "constant/polyMesh").mkdir(parents=True)
            (case / "case-report.json").write_text('{}\n')
            (case / "log.checkMesh").write_text("cells: 1\nMesh OK.\n")
            p = case / "constant/polyMesh/boundary"
            p.write_text("inlet { type patch; nFaces 1; } outlet { type patch; nFaces 1; } walls { type patch; nFaces 4; }")
            with self.assertRaises(ValueError): gate.accept(case)
            p.write_text(p.read_text().replace("walls { type patch", "walls { type wall"))
            gate.accept(case)
            self.assertEqual(json.loads((case / "mesh-report.json").read_text())["cells"], 1)

    def test_geometry_receipt_and_images_are_bound_without_releasing_hardware(self):
        family = SOURCE.parents[1]
        report = json.loads((family / "derived/flow4l/study-report.json").read_text())
        for name, digest in report["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        self.assertFalse(any(report["qualification"].values()))
        self.assertTrue(all(v["surface_components"] == 1 for v in report["mesh_metrics"].values()))
        self.assertTrue(all(p["mean_speed_at_budget_flow_m_s"] < 3 for p in report["coolant_terminal_sections"]))
        for name, image in report["images"].items():
            self.assertEqual(hashlib.sha256((family / "derived/flow4l/views" / name).read_bytes()).hexdigest(), image["sha256"])
        design = json.loads((SOURCE / "design.json").read_text())
        self.assertTrue(all(v is None for v in design["required_measured_interfaces"].values()))
        self.assertFalse(any(design["qualification"].values()))


if __name__ == "__main__":
    unittest.main()
