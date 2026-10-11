"""Independent geometry gates on tiny synthetic meshes; no engineering claims."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from _deps import require_modules

require_modules("numpy", "scipy", "trimesh")
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/bionic-turbo-f0/inspect_mesh.py"
SPEC = importlib.util.spec_from_file_location("bionic_inspect", SCRIPT)
INSPECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSPECT)


class BionicInspectionTests(unittest.TestCase):
    def setUp(self):
        self.box = trimesh.creation.box(extents=(2, 3, 4))

    def test_cli_imports_without_shadowing_standard_library(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("directory", result.stdout)

    def test_closed_box_passes_without_dropping_triangles(self):
        report, mesh = INSPECT.inspect_triangles(self.box.triangles)
        self.assertTrue(report["passed"])
        self.assertEqual(report["surface_components"], 1)
        self.assertEqual(report["signed_volume_mm3"], 24)
        self.assertEqual(report["triangles"], 12)
        self.assertTrue(report["all_input_triangles_retained"])
        np.testing.assert_array_equal(mesh.triangles, self.box.triangles)

    def test_open_inverted_duplicate_and_multiple_shells_fail(self):
        other = self.box.copy()
        other.apply_translation((10, 0, 0))
        cases = (
            (self.box.triangles[:-1], "boundary_edges"),
            (self.box.triangles[:, ::-1], "nonpositive_component_volume"),
            (np.concatenate((self.box.triangles, self.box.triangles[:1])), "duplicate_triangles"),
            (np.concatenate((self.box.triangles, other.triangles)), "not_one_connected_surface"),
        )
        for triangles, failure in cases:
            with self.subTest(failure=failure):
                report, _ = INSPECT.inspect_triangles(triangles)
                self.assertFalse(report["passed"])
                self.assertIn(failure, report["failures"])
                self.assertEqual(report["triangles"], len(triangles))
                self.assertTrue(report["all_input_triangles_retained"])

    def test_empty_nonfinite_and_degenerate_fail(self):
        for triangles in (np.empty((0, 3, 3)), np.full((1, 3, 3), np.nan)):
            with self.assertRaises(ValueError):
                INSPECT.inspect_triangles(triangles)
        triangles = self.box.triangles.copy()
        triangles[0, 1] = triangles[0, 0]
        report, _ = INSPECT.inspect_triangles(triangles)
        self.assertIn("degenerate_triangles", report["failures"])

    def test_binary_exports_are_hash_bound_and_truncation_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            generation = {"files": []}
            for name in ("housing", "flow-domain", "section"):
                path = directory / f"{name}.stl"
                self.box.export(path)
                generation["files"].append({"file": path.name, "sha256": INSPECT.sha256(path), "triangles": 12})
            (directory / "report.json").write_text(json.dumps(generation))
            report, _ = INSPECT.inspect_outputs(directory)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(len(report["sources"]), 4)
            self.assertFalse(report["engineering_validated"])
            self.assertFalse(report["manufacturing_authorized"])
            generation["files"][0]["sha256"] = "0" * 64
            (directory / "report.json").write_text(json.dumps(generation))
            report, _ = INSPECT.inspect_outputs(directory)
            self.assertEqual(report["status"], "failed")
            self.assertIn("housing: generation_sha256_mismatch", report["errors"])
            path = directory / "housing.stl"
            path.write_bytes(path.read_bytes()[:-1])
            report, _ = INSPECT.inspect_outputs(directory)
            self.assertEqual(report["status"], "failed")
            self.assertIn("housing: binary_stl_length_mismatch", report["errors"])


if __name__ == "__main__":
    unittest.main()
