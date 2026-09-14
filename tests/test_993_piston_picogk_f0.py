import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/993-m64-60-piston-gallery-f0/evidence/picogk-f0"


class PistonPicogkF0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screen = json.loads(
            (EVIDENCE / "picogk-optimization-screen.json").read_text()
        )
        cls.integrity = json.loads(
            (EVIDENCE / "picogk-output-integrity.json").read_text()
        )

    def test_real_picogk_runtime_is_bound(self):
        runtime = self.screen["runtime"]
        self.assertTrue(self.screen["executed"])
        self.assertEqual(runtime["picogk_version"], "2.3.0")
        self.assertEqual(runtime["native_runtime_abi"], "picogk.26.2")
        self.assertEqual(runtime["voxel_size_mm"], 0.5)
        self.assertRegex(runtime["native_image_id"], r"^sha256:[0-9a-f]{64}$")

    def test_no_variant_is_selected_or_released(self):
        self.assertEqual(len(self.screen["variants"]), 6)
        self.assertIsNone(self.screen["decision"]["selected_variant"])
        self.assertFalse(self.screen["decision"]["manufacturing_authorized"])
        self.assertFalse(self.screen["decision"]["engine_operation_authorized"])
        self.assertTrue(
            all(not variant["eligible_for_selection"] for variant in self.screen["variants"])
        )

    def test_mass_reduction_does_not_override_strength_constraint(self):
        lightest = min(
            self.screen["variants"], key=lambda variant: variant["geometry"]["mass_g"]
        )
        self.assertLess(lightest["geometry"]["mass_change_from_brep_percent"], -1.5)
        self.assertFalse(lightest["structural_screen"]["passes_target"])
        self.assertLess(
            lightest["structural_screen"]["ambient_yield_to_stress_ratio"],
            lightest["structural_screen"]["target_ambient_yield_ratio"],
        )

    def test_raw_mesh_gate_is_failed_without_repair(self):
        self.assertEqual(self.integrity["status"], "failed_output_mesh_integrity")
        self.assertTrue(self.integrity["all_hashes_match"])
        self.assertFalse(self.integrity["all_meshes_watertight"])
        self.assertFalse(
            self.integrity["decision"]["picogk_geometry_gate_passed"]
        )
        self.assertFalse(self.integrity["decision"]["repair_attempted"])
        self.assertTrue(
            all(item["boundary_edge_count"] == 0 for item in self.integrity["variants"])
        )
        self.assertTrue(
            all(item["nonmanifold_edge_count"] > 0 for item in self.integrity["variants"])
        )


if __name__ == "__main__":
    unittest.main()
