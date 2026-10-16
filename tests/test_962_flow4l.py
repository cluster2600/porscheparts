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
spec = importlib.util.spec_from_file_location("flow4l_solution_fields", SOURCE / "analyze_flow.py")
fields = importlib.util.module_from_spec(spec); spec.loader.exec_module(fields)
spec = importlib.util.spec_from_file_location("flow4l_native_case", SOURCE / "prepare_native_tet_case.py")
native_case = importlib.util.module_from_spec(spec); spec.loader.exec_module(native_case)


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

    def test_flux_comes_from_the_same_saved_solution_and_checks_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phi"
            path.write_text("dimensions [0 3 -1 0 0 0 0]; inlet { value nonuniform List<scalar> 2 (-0.3 -0.7); }")
            self.assertAlmostEqual(fields.patch_flux(path, "inlet", 2), -1)
            with self.assertRaises(ValueError): fields.patch_flux(path, "inlet", 3)
            path.write_text("dimensions [0 3 -1 0 0 0 0]; inlet { value uniform -0.5; }")
            self.assertEqual(fields.patch_flux(path, "inlet", 2), -1)
            path.write_text("dimensions [0 3 -1 0 0 0 0]; inlet { value uniform 1e999; }")
            with self.assertRaises(ValueError): fields.patch_flux(path, "inlet", 2)
            path.write_text(path.read_text().replace("0 3 -1", "1 0 -1"))
            with self.assertRaises(ValueError): fields.patch_flux(path, "inlet", 2)

    def test_native_case_preserves_inputs_and_rejects_bad_decomposition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); template = root / "template"; parent = root / "parent"
            for name in ("0", "constant", "system"): (template / name).mkdir(parents=True)
            (template / "0/U").write_text("initial velocity")
            (template / "case-report.json").write_text(json.dumps({"case_hashes": {"0/U": native_case.sha(template / "0/U")}}))
            (parent / "constant/geometry").mkdir(parents=True)
            (parent / "constant/polyMesh").mkdir()
            (parent / "constant/geometry/coolant.obj").write_text("surface")
            (parent / "case-report.json").write_text('{}')
            mesh = root / "mesh.msh"; mesh.write_text("mesh")
            grid = root / "grid.json"; grid.write_text("grid")
            log = root / "export.log"
            log.write_text("Native tetrahedra: 1; minimum volume: -1; sum: 1; parent: 1; relative volume difference: 0\nEnd\n")
            with self.assertRaises(ValueError): native_case.prepare(parent, mesh, log, template, grid, root / "rejected")
            self.assertFalse((root / "rejected").exists())
            log.write_text(log.read_text().replace("volume: -1", "volume: 1"))
            output = root / "accepted"
            native_case.prepare(parent, mesh, log, template, grid, output)
            report = json.loads((output / "case-report.json").read_text())
            self.assertEqual(report["cells"], 1)
            self.assertEqual(report["case_hashes"]["0/U"], native_case.sha(template / "0/U"))
            self.assertIn("not_yet_accepted", report["status"])
            with self.assertRaises(ValueError): native_case.prepare(parent, mesh, log, template, grid, output)


if __name__ == "__main__":
    unittest.main()
