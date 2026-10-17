"""Independent geometric witnesses and retained diagnostic provenance."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"
spec = importlib.util.spec_from_file_location("coolant_boundaries", FAMILY / "source/audit_coolant_boundaries.py")
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)


class CoolantBoundaryReceiptTests(unittest.TestCase):
    def test_diagnostic_cannot_become_cfd_or_manufacturing_evidence(self):
        report = json.loads((FAMILY / "derived/boundary-audit.json").read_text())
        self.assertEqual(report["status"], "sampled_interface_diagnostic_not_cfd_ready")
        for key in ("manufacturing_authorized", "is_fitment_validated", "hydraulic_performance_validated",
                    "wall_thickness_qualified", "interface_conformity_validated"):
            self.assertIs(report[key], False)
        for path, digest in report["source_hashes"].items():
            self.assertEqual(hashlib.sha256((FAMILY / path).read_bytes()).hexdigest(), digest)
        self.assertEqual(hashlib.sha256((FAMILY / "derived/boundary-probes.png").read_bytes()).hexdigest(),
                         report["output_hashes"]["boundary-probes.png"])
        original = json.loads((FAMILY / "derived/study-report.json").read_text())
        for name, digest in report["original_mesh_hashes"].items():
            self.assertEqual(digest, original["mesh_metrics"][name]["sha256"])
        for row in report["probes"]:
            self.assertEqual(row["samples"], sum(row[k] for k in ("metal_only", "water_only", "overlap", "unassigned")))
            self.assertEqual(row["samples"] + report["excluded_terminal_face_samples"],
                             original["mesh_metrics"]["coolant"]["triangles"])
        self.assertGreater(report["probes"][0]["unassigned"], 0)


@unittest.skipUnless(importlib.util.find_spec("numpy"), "optional NumPy runtime unavailable")
class CoolantProbeTests(unittest.TestCase):
    def test_exact_shell_and_removed_half_wall_are_distinguished(self):
        import numpy as np
        centers = np.array(((1., 0, 0), (-1., 0, 0)))
        water = lambda p: np.linalg.norm(p) - 1
        shell = lambda p: max(np.linalg.norm(p) - 3, 1 - np.linalg.norm(p))
        rows, _, excluded = audit.probes(centers, centers, shell, water, (-4, 4))
        self.assertEqual(excluded, 0)
        self.assertTrue(all(r["metal_only"] == 2 and r["unassigned"] == 0 for r in rows))
        punctured = lambda p: max(shell(p), p[0])
        rows, _, _ = audit.probes(centers, centers, punctured, water, (-4, 4))
        self.assertTrue(all(r["unassigned"] == 1 for r in rows))

    def test_fluid_reentry_is_not_hidden_as_a_material_pass(self):
        rows, _, _ = audit.probes([[0, 0, 0]], [[1, 0, 0]], lambda p: 1, lambda p: -1, (-4, 4))
        self.assertTrue(all(r["water_only"] == 1 and r["metal_only"] == 0 for r in rows))
        rows, _, _ = audit.probes([[0, 0, 0]], [[1, 0, 0]], lambda p: -1, lambda p: -1, (-4, 4))
        self.assertTrue(all(r["overlap"] == 1 for r in rows))

    def test_invalid_sampling_never_produces_a_diagnostic(self):
        import numpy as np
        for centers, normals in (([], []), ([[np.nan, 0, 0]], [[1, 0, 0]]),
                                 ([[0, 0, 0]], [[2, 0, 0]])):
            with self.assertRaises(ValueError):
                audit.probes(centers, normals, lambda p: -1, lambda p: 1, (-4, 4))
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            audit.probes([[0, 0, 0]], [[1, 0, 0]], lambda p: np.inf, lambda p: 1, (-4, 4))


@unittest.skipUnless(importlib.util.find_spec("vtk"), "optional VTK runtime unavailable")
class CoolantSectionTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("trimesh"), "optional trimesh runtime unavailable")
    def test_modified_input_cannot_export_ports_or_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "solid.stl").write_bytes(b"not the retained mesh")
            output = root / "output"
            with self.assertRaisesRegex(ValueError, "differs from retained"):
                audit.audit(root, output)
            self.assertFalse(output.exists())

    def test_cube_section_matches_independent_area_and_perimeter(self):
        import vtk
        cube = vtk.vtkCubeSource(); cube.Update()
        _, result = audit.section(cube.GetOutput(), 0)
        self.assertAlmostEqual(result["area_mm2"], 1)
        self.assertAlmostEqual(result["perimeter_mm"], 4)
        self.assertAlmostEqual(result["hydraulic_diameter_mm"], 1)

    def test_disconnected_and_open_sections_are_rejected(self):
        import vtk
        append = vtk.vtkAppendPolyData()
        for y in (-2, 2):
            cube = vtk.vtkCubeSource(); cube.SetCenter(0, y, 0); cube.Update()
            append.AddInputData(cube.GetOutput())
        append.Update()
        with self.assertRaisesRegex(ValueError, "one port loop"):
            audit.section(append.GetOutput(), 0)
        plane = vtk.vtkPlaneSource(); plane.Update()
        with self.assertRaisesRegex(ValueError, "closed loop"):
            audit.section(plane.GetOutput(), 0)


if __name__ == "__main__":
    unittest.main()
