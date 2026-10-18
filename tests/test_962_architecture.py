"""Photo and AI proposals must remain distinct from measured or qualified engineering."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"


class ArchitectureTests(unittest.TestCase):
    def test_library_drift_is_rejected_before_output(self):
        s = importlib.util.spec_from_file_location("architecture", FAMILY / "source/architecture/inspect_and_render.py")
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "ShapeKernel source differs"):
                m.inspect(root, root, root, root / "output")
            self.assertFalse((root / "output").exists())

    def test_actual_geometry_and_images_are_bound_without_engineering_approval(self):
        r = json.loads((FAMILY / "derived/architecture-report.json").read_text())
        for flag in ("manufacturing_authorized", "is_fitment_validated", "material_qualified",
                     "hydraulic_performance_validated", "thermal_improvement_validated", "strength_validated",
                     "wall_thickness_qualified", "interface_conformity_validated"):
            self.assertIs(r[flag], False)
        for relative, digest in r["source_hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
        for n, item in r["mesh_metrics"].items():
            self.assertTrue(item["watertight"] and item["consistent_winding"])
            self.assertEqual(item["surface_components"], 1)
            self.assertEqual(r["native_reports"][n]["voxel_mm"], .5)
            self.assertGreater(item["volume_mm3"], 0)
        self.assertGreater(r["sampled_water_dry_clearance_mm"], 4)
        self.assertEqual(len(r["dry_opening_probes_mm"]), 8)
        for p in r["gas_port_sections_rotated_z_90deg"]:
            self.assertLess(abs(p["area_mm2"] / r["analytic_gas_port_area_mm2"] - 1), .02)
        for n, item in r["images"].items():
            data = (FAMILY / "derived/architecture-views" / (n + ".png")).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            self.assertEqual(struct.unpack(">II", data[16:24]), (1600, 1200))

    def test_observed_photos_have_no_claimed_scale_or_redistribution(self):
        reference = json.loads((FAMILY / "source/architecture/references.json").read_text())
        self.assertIsNone(reference["donor_engine"])
        self.assertFalse(reference["manufacturing_authorized"])
        for p in reference["photos"]:
            self.assertIsNone(p["scale"])
            self.assertIsNone(p["dimension_mm"])
            self.assertFalse(p["pixels_committed"])

    def test_qwen_bad_methods_are_rejected_and_only_the_expression_is_retained(self):
        root = FAMILY / "derived/qwen-assistance"
        review = json.loads((root / "review.json").read_text())
        self.assertFalse(review["r3"]["accepted"])
        self.assertFalse(review["base_method"]["accepted"])
        self.assertTrue(review["base_radius"]["accepted"])
        for name in ("r3", "base-method", "base-radius"):
            d = root / name; r = json.loads((d / "qwen-report.json").read_text())
            for field, file in (("prompt_sha256", "qwen-prompt.txt"), ("response_sha256", "response.txt"),
                                ("runner_sha256", "runner.py")):
                self.assertEqual(hashlib.sha256((d / file).read_bytes()).hexdigest(), r[field])
            self.assertFalse(r["generated_code_executed"])
            self.assertFalse(r["engineering_approval"])
            self.assertGreater(r["generated_tokens"], 0)

    def test_invalid_specifications_produced_no_mesh(self):
        r = json.loads((FAMILY / "source/architecture/rejected-inputs.json").read_text())
        self.assertEqual(len(r["cases"]), 5)
        self.assertTrue(all(c["returncode"] != 0 and not c["mesh_created"] for c in r["cases"]))


if __name__ == "__main__":
    unittest.main()
