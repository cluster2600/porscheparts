import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/993-m64-60-piston-gallery-f0"
EVIDENCE = TWIN / "evidence/picogk-f1-manifold-output"


class PistonPicogkManifoldOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screen = json.loads((EVIDENCE / "picogk-optimization-screen.json").read_text())
        cls.integrity = json.loads((EVIDENCE / "picogk-output-integrity.json").read_text())

    def test_integrity_gate_passes_on_every_variant(self):
        self.assertEqual(self.integrity["status"], "passed_output_mesh_integrity")
        self.assertTrue(self.integrity["all_hashes_match"])
        self.assertTrue(self.integrity["decision"]["picogk_geometry_gate_passed"])
        self.assertFalse(self.integrity["decision"]["manufacturing_authorized"])
        self.assertEqual(len(self.integrity["variants"]), 6)
        for item in self.integrity["variants"]:
            self.assertTrue(item["watertight"], item["variant_id"])
            self.assertEqual(item["nonmanifold_edge_count"], 0)
            self.assertEqual(item["boundary_edge_count"], 0)
            self.assertEqual(item["body_count"], 1)

    def test_output_stage_only_drops_degenerate_triangles(self):
        self.assertIn("no vertex moved", self.screen["runtime"]["output_stage"])
        for variant in self.screen["variants"]:
            geometry = variant["geometry"]
            self.assertEqual(
                geometry["raw_triangle_count"] - geometry["removed_coincident_vertex_triangles"],
                geometry["triangle_count"],
            )

    def test_integrity_is_bound_to_this_screen(self):
        import hashlib

        digest = hashlib.sha256((EVIDENCE / "picogk-optimization-screen.json").read_bytes()).hexdigest()
        self.assertEqual(self.integrity["source_screen_sha256"], digest)
        screen_hashes = {v["variant_id"]: v["geometry"]["output_sha256"] for v in self.screen["variants"]}
        self.assertEqual(set(screen_hashes), {i["variant_id"] for i in self.integrity["variants"]})

    def test_design_selection_is_recorded_as_none(self):
        decision = self.screen["decision"]
        self.assertIsNone(decision["selected_variant"])
        self.assertFalse(decision["manufacturing_authorized"])
        self.assertFalse(decision["engine_operation_authorized"])
        self.assertTrue(all(not v["eligible_for_selection"] for v in self.screen["variants"]))
        self.assertTrue(all(not v["structural_screen"]["passes_target"] for v in self.screen["variants"]))

    def test_frozen_f0_evidence_still_records_the_raw_failure(self):
        f0 = json.loads((TWIN / "evidence/picogk-f0/picogk-output-integrity.json").read_text())
        self.assertEqual(f0["status"], "failed_output_mesh_integrity")


if __name__ == "__main__":
    unittest.main()
