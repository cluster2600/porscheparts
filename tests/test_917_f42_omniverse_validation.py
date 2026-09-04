import hashlib
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f42-omniverse-validation"
SUMMARY = EVIDENCE / "f42-omniverse-validation-summary.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F42OmniverseValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(SUMMARY.read_text())

    def test_geometry_is_bounded_and_private(self):
        geometry = self.summary["geometry"]
        self.assertEqual(geometry["mesh_count"], 1)
        self.assertEqual(geometry["point_count"], 34313)
        self.assertEqual(geometry["triangle_count"], 68678)
        self.assertEqual(geometry["boundary_edge_count"], 0)
        self.assertEqual(geometry["nonmanifold_edge_count"], 0)
        self.assertTrue(geometry["watertight_after_exact_seam_weld"])
        self.assertEqual(geometry["coordinate_displacement_from_weld"], 0.0)
        self.assertFalse(geometry["usd_published"])
        self.assertFalse(self.summary["input"]["source_geometry_published"])

    def test_official_validator_results_are_not_overclaimed(self):
        workflow = self.summary["official_nvidia_workflow"]
        self.assertEqual(workflow["preflight"]["status"], "ready")
        self.assertEqual(workflow["minimum_usd"]["status"], "pass")
        self.assertEqual(workflow["asset_validator"]["status"], "pass")
        self.assertEqual(workflow["geometry_validator"]["status"], "pass")
        self.assertEqual(workflow["physics_validator"]["status"], "pass")
        self.assertEqual(workflow["ovrtx"]["status"], "pass")
        self.assertEqual(workflow["ovrtx"]["frames_rendered"], 24)
        self.assertTrue(workflow["ovrtx"]["all_frames_non_uniform"])
        self.assertEqual(workflow["cad_to_usd_router"]["status"], "fail")
        self.assertEqual(workflow["simready_profile"]["status"], "fail")

    def test_fail_closed_release_gates(self):
        self.assertEqual(self.summary["status"], "needs_rerun")
        gates = self.summary["gates"]
        self.assertTrue(gates["topology_closed"])
        self.assertTrue(gates["usd_minimum_valid"])
        self.assertTrue(gates["native_ovrtx_render_valid"])
        for key in (
            "official_cad_to_usd_route_complete",
            "simready_profile_valid",
            "physical_properties_authored",
            "material_card_qualified",
            "thermal_validation_complete",
            "structural_validation_complete",
            "metal_print_authorized",
            "engine_start_authorized",
        ):
            self.assertFalse(gates[key])

    def test_published_media_hashes_and_scope(self):
        publication = self.summary["publication"]
        self.assertEqual(len(publication["images"]), 5)
        for image in publication["images"]:
            path = ROOT / image["path"]
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(sha256(path), image["sha256"])
        video = publication["video"]
        video_path = ROOT / video["path"]
        self.assertIn(b"ftyp", video_path.read_bytes()[:32])
        self.assertEqual(sha256(video_path), video["sha256"])
        self.assertEqual(video["codec"], "h264")
        self.assertEqual(video["pixel_format"], "yuv420p")
        self.assertFalse(video["is_functional_simulation"])
        self.assertFalse(publication["all_images_are_solver_results"])
        self.assertFalse(publication["raw_reports_published"])

    def test_rented_runtime_was_closed_after_recovery(self):
        runtime = self.summary["runtime"]
        self.assertEqual(runtime["gpu_memory_mib"], 97887)
        self.assertEqual(runtime["cpu_cores_effective"], 32)
        self.assertTrue(runtime["native_ovrtx_render_executed"])
        self.assertFalse(runtime["material_assignment_executed"])
        self.assertFalse(runtime["physics_assignment_executed"])
        self.assertTrue(runtime["instance_destroyed_after_recovery"])

    def test_summary_has_no_private_runtime_path(self):
        payload = SUMMARY.read_text()
        self.assertNotIn("/workspace/", payload)
        self.assertNotIn("/private/tmp/", payload)
        self.assertNotIn("/Users/", payload)


if __name__ == "__main__":
    unittest.main()
