import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LPBF = ROOT / "twins/993-m64-60-piston-gallery-f0/evidence/lpbf-f0"
SIMREADY = ROOT / "twins/993-m64-60-piston-gallery-f0/evidence/simready-f0"
REPORT = LPBF / "993-eng-piston-cp1-gallery-f0-0001-lpbf-geometry-report.json"
METRICS = LPBF / "993-eng-piston-cp1-gallery-f0-0001-layer-metrics.csv"
MANIFEST = LPBF / "993-eng-piston-cp1-gallery-f0-0001-lpbf-geometry-manifest.json"
SUMMARY = SIMREADY / "simready-validation-summary.json"
BUILD_SCREEN = LPBF / "omniverse-build-screen-summary.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PistonLpbfOmniverseF0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.simready = json.loads(SUMMARY.read_text(encoding="utf-8"))
        cls.build_screen = json.loads(BUILD_SCREEN.read_text(encoding="utf-8"))
        with METRICS.open("r", encoding="utf-8", newline="") as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_surface_is_hash_bound_watertight_and_single_component(self) -> None:
        surface = self.report["analysis_surface"]
        self.assertEqual(surface["vertices"], 136988)
        self.assertEqual(surface["triangles"], 273988)
        self.assertTrue(surface["watertight"])
        self.assertTrue(surface["single_component"])
        self.assertEqual(surface["sha256"], "b2eb753c41a62ae28cb354fc59a8267b6619e1e75539972778a25f53508393fd")
        self.assertEqual(self.report["master"]["sha256"], digest(ROOT / "parts/993-eng-piston-cp1-gallery-f0-0001/derived/piston_cp1_gallery_f0.step"))

    def test_all_2390_layers_are_present_and_finite(self) -> None:
        slicing = self.report["full_build_slicing"]
        self.assertEqual(slicing["layer_count"], 2390)
        self.assertEqual(slicing["layer_thickness_mm"], 0.05)
        self.assertEqual(slicing["empty_internal_layers"], 0)
        self.assertEqual(len(self.rows), 2390)
        for index, row in enumerate(self.rows):
            self.assertEqual(int(row["layer_index"]), index)
            self.assertGreaterEqual(float(row["z_mm"]), 0.0)
            for key, value in row.items():
                if key != "layer_index":
                    self.assertGreaterEqual(float(value), 0.0)

    def test_geometric_screen_does_not_claim_process_release(self) -> None:
        self.assertEqual(self.report["selected_candidate_orientation"], "roll_y_45")
        self.assertEqual(self.report["full_build_slicing"]["new_island_count"], 4)
        self.assertAlmostEqual(self.report["full_build_slicing"]["support_proxy_volume_cm3"], 8.3654375)
        self.assertAlmostEqual(self.report["thickness_screen"]["p01_mm"], 0.4201932836711133)
        self.assertFalse(self.report["process_physics"]["additivefoam_executed"])
        self.assertFalse(self.report["process_physics"]["target_material_card_complete_and_calibrated"])
        self.assertTrue(self.report["gates"]["full_piece_layer_slicing_completed"])
        self.assertFalse(self.report["gates"]["candidate_orientation_engineering_reviewed"])
        self.assertFalse(self.report["gates"]["recoater_clearance_validated"])
        self.assertFalse(self.report["gates"]["metal_print_authorized"])

    def test_lpbf_public_artifacts_are_hash_bound(self) -> None:
        expected = {
            "report": REPORT,
            "layer_metrics": METRICS,
            "image": LPBF / "993-eng-piston-cp1-gallery-f0-0001-lpbf-geometry-screen.png",
        }
        for name, path in expected.items():
            self.assertEqual(self.manifest["artifacts"][name]["sha256"], digest(path))
        self.assertFalse(self.manifest["gates"]["contains_machine_file"])
        self.assertFalse(self.manifest["gates"]["metal_print_authorized"])

    def test_simready_pass_is_limited_to_isolated_asset(self) -> None:
        validators = self.simready["validators"]
        self.assertEqual(validators["nvidia_asset_validator"], "PASS")
        self.assertEqual(validators["geometry_category"], "PASS")
        self.assertEqual(validators["physics_category"], "PASS")
        self.assertEqual(validators["simready_profile"]["status"], "PASS")
        authored = self.simready["authored_screening_properties"]
        self.assertIsNone(authored["friction"])
        self.assertIsNone(authored["restitution"])
        self.assertIsNone(authored["gravity_scene"])
        gates = self.simready["gates"]
        self.assertTrue(gates["simready_isolated_asset_passed"])
        self.assertFalse(gates["omniverse_assembly_function_tested"])
        self.assertFalse(gates["manufacturing_authorized"])
        for entry in self.simready["public_media"].values():
            self.assertEqual(entry["sha256"], digest(SIMREADY / entry["path"]))

    def test_omniverse_build_screen_is_hash_bound_and_fail_closed(self) -> None:
        scene = self.build_screen
        self.assertEqual(scene["build_scene"]["orientation"], "roll_y_45")
        self.assertTrue(scene["build_scene"]["candidate_grounded_on_plate"])
        self.assertTrue(scene["build_scene"]["bare_part_inside_nominal_machine_envelope"])
        for status in scene["validators"].values():
            self.assertEqual(status, "PASS")
        image = scene["render"]["image"]
        self.assertEqual(image["sha256"], digest(LPBF / image["path"]))
        self.assertTrue(scene["render"]["visually_inspected"])
        self.assertFalse(scene["gates"]["distortion_field_applied"])
        self.assertFalse(scene["gates"]["recoater_collision_validated"])
        self.assertFalse(scene["gates"]["omniverse_assembly_function_tested"])
        self.assertFalse(scene["gates"]["metal_print_authorized"])


if __name__ == "__main__":
    unittest.main()
