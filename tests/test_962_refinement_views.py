"""Resolution changes may improve geometry sampling, never grant physical release."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"
spec = importlib.util.spec_from_file_location("head_views", FAMILY / "source/refine_and_render.py")
views = importlib.util.module_from_spec(spec); spec.loader.exec_module(views)


class RefinementViewsTests(unittest.TestCase):
    def test_another_executable_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            with self.assertRaisesRegex(ValueError, "pinned Engine.dll"):
                views.run(root / "other.dll", output)
            self.assertFalse(output.exists())

    def test_only_resolution_changes_and_original_spec_is_untouched(self):
        path = FAMILY / "source/solid.json"
        before = path.read_bytes()
        expected = json.loads(before); expected["voxel_mm"] = .5
        self.assertEqual(views.refined_spec(path), expected)
        self.assertEqual(path.read_bytes(), before)
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "source.json"
            for key, value in (("voxel_mm", 1), ("status", "manufacturing_ready")):
                data = json.loads(before); data[key] = value
                altered.write_text(json.dumps(data))
                with self.assertRaises(ValueError): views.refined_spec(altered)

    def test_actual_generation_and_images_are_bound_without_release(self):
        report = json.loads((FAMILY / "derived/refinement-report.json").read_text())
        self.assertEqual(report["refined_voxel_mm"], .5)
        for flag in ("manufacturing_authorized", "is_fitment_validated", "hydraulic_performance_validated",
                     "thermal_improvement_validated", "interface_conformity_validated", "wall_thickness_qualified"):
            self.assertIs(report[flag], False)
        for path, digest in report["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        for path, digest in report["geometry_reference_source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        for name, item in report["execution_inputs"].items():
            data = json.loads((ROOT / item["reference"]).read_text()); data["voxel_mm"] = .5
            actual = (json.dumps(data, indent=2) + "\n").encode()
            self.assertEqual(hashlib.sha256(actual).hexdigest(), item["input_sha256"])
            self.assertEqual(report["native_reports"][name]["voxel_mm"], .5)
            mesh = report["mesh_metrics"][name]
            self.assertTrue(mesh["watertight"] and mesh["consistent_winding"])
            self.assertEqual(mesh["connected_components"], 1)
        for name, item in report["images"].items():
            data = (FAMILY / "derived/views" / (name + ".png")).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack(">II", data[16:24]), (item["width"], item["height"]))


if __name__ == "__main__":
    unittest.main()
