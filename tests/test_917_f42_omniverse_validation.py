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
        self.assertEqual(geometry["vertex_count"], 34313)
        self.assertEqual(geometry["triangle_count"], 68678)
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
        self.assertEqual(workflow["cad_to_usd_router"]["status"], "fail")
        self.assertEqual(workflow["simready_profile"]["status"], "fail")

    def test_fail_closed_release_gates(self):
        self.assertEqual(self.summary["status"], "needs_rerun")
        gates = self.summary["gates"]
        self.assertTrue(gates["usd_minimum_valid"])
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

    def test_published_image_hash_and_scope(self):
        image = self.summary["publication"]["image"]
        self.assertEqual(sha256(ROOT / image["path"]), image["sha256"])
        self.assertFalse(image["is_solver_result"])
        self.assertFalse(self.summary["publication"]["raw_reports_published"])

    def test_summary_has_no_private_runtime_path(self):
        payload = SUMMARY.read_text()
        self.assertNotIn("/workspace/", payload)
        self.assertNotIn("/private/tmp/", payload)
        self.assertNotIn("/Users/", payload)


if __name__ == "__main__":
    unittest.main()
