import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/993-oval-exhaust-tip-in625-f0"
LPBF = TWIN / "evidence/lpbf-f0"
OPENFOAM = TWIN / "evidence/openfoam-f0"
SIMREADY = TWIN / "evidence/simready-f0"
PART = ROOT / "parts/993-exh-oval-tip-in625-f0-0001"
REPORT = LPBF / "993-exh-oval-tip-in625-f0-0001-lpbf-geometry-report.json"
METRICS = LPBF / "993-exh-oval-tip-in625-f0-0001-layer-metrics.csv"
MANIFEST = LPBF / "993-exh-oval-tip-in625-f0-0001-lpbf-geometry-manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OvalExhaustTipLpbfOmniverseF0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.openfoam = json.loads(
            (PART / "evidence/openfoam-flow-screen.json").read_text(encoding="utf-8")
        )
        cls.openfoam_audit = json.loads(
            (OPENFOAM / "openfoam-evidence-audit.json").read_text(encoding="utf-8")
        )
        cls.simready = json.loads(
            (SIMREADY / "simready-validation-summary.json").read_text(encoding="utf-8")
        )
        cls.build_screen = json.loads(
            (LPBF / "omniverse-build-screen-summary.json").read_text(encoding="utf-8")
        )
        with METRICS.open("r", encoding="utf-8", newline="") as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_surface_is_hash_bound_watertight_and_single_component(self) -> None:
        surface = self.report["analysis_surface"]
        self.assertEqual(surface["vertices"], 234967)
        self.assertEqual(surface["triangles"], 469950)
        self.assertTrue(surface["watertight"])
        self.assertTrue(surface["single_component"])
        self.assertEqual(
            surface["sha256"],
            "85b332bba05a4dcf434adff1613b9ef17fe3ac5bcb12bddd8d746eeee4f6b74a",
        )
        master = PART / "derived/oval_exhaust_tip_in625_f0.step"
        self.assertEqual(self.report["master"]["sha256"], digest(master))

    def test_all_3702_layers_are_present_and_finite(self) -> None:
        slicing = self.report["full_build_slicing"]
        self.assertEqual(slicing["orientation"], "roll_y_25")
        self.assertEqual(slicing["build_envelope_type"], "rectangular_prism")
        self.assertEqual(slicing["layer_count"], 3702)
        self.assertEqual(slicing["layer_thickness_mm"], 0.04)
        self.assertEqual(slicing["empty_internal_layers"], 0)
        self.assertEqual(len(self.rows), 3702)
        for index, row in enumerate(self.rows):
            self.assertEqual(int(row["layer_index"]), index)
            for key, value in row.items():
                if key != "layer_index":
                    self.assertGreaterEqual(float(value), 0.0)

    def test_lpbf_geometry_screen_is_fail_closed(self) -> None:
        slicing = self.report["full_build_slicing"]
        self.assertEqual(slicing["new_island_count"], 1)
        self.assertEqual(slicing["layers_with_unsupported_area"], 784)
        self.assertAlmostEqual(slicing["support_proxy_volume_cm3"], 7.193970000000013)
        self.assertAlmostEqual(self.report["thickness_screen"]["p01_mm"], 0.6358603292676219)
        self.assertEqual(self.report["thickness_screen"]["sample_fraction_below_1p5_mm"], 1.0)
        self.assertFalse(self.report["process_physics"]["additivefoam_executed"])
        self.assertFalse(
            self.report["process_physics"]["target_material_card_complete_and_calibrated"]
        )
        gates = self.report["gates"]
        self.assertTrue(gates["full_piece_layer_slicing_completed"])
        self.assertFalse(gates["candidate_orientation_engineering_reviewed"])
        self.assertFalse(gates["recoater_clearance_validated"])
        self.assertFalse(gates["metal_print_authorized"])

    def test_lpbf_public_artifacts_are_hash_bound(self) -> None:
        expected = {
            "report": REPORT,
            "layer_metrics": METRICS,
            "image": LPBF / "993-exh-oval-tip-in625-f0-0001-lpbf-geometry-screen.png",
        }
        for name, path in expected.items():
            self.assertEqual(self.manifest["artifacts"][name]["sha256"], digest(path))
        self.assertFalse(self.manifest["gates"]["contains_machine_file"])
        self.assertFalse(self.manifest["gates"]["contains_supplier_support_geometry"])
        self.assertFalse(self.manifest["gates"]["metal_print_authorized"])

    def test_openfoam_evidence_is_recomputed_and_not_converged_in_grid(self) -> None:
        cases = self.openfoam["cases"]
        self.assertEqual([case["mesh"]["tetrahedra"] for case in cases], [12622, 40186, 91086])
        coarse_previous = cases[-2]["results"]
        fine = cases[-1]["results"]
        pressure_change = abs(
            fine["bulk_total_pressure_drop_pa"] - coarse_previous["bulk_total_pressure_drop_pa"]
        ) / abs(fine["bulk_total_pressure_drop_pa"])
        velocity_change = abs(
            fine["outlet_area_average_speed_m_s"] - coarse_previous["outlet_area_average_speed_m_s"]
        ) / abs(fine["outlet_area_average_speed_m_s"])
        self.assertAlmostEqual(
            self.openfoam_audit["recomputed_grid_change"]["bulk_total_pressure_drop_relative"],
            pressure_change,
        )
        self.assertAlmostEqual(
            self.openfoam_audit["recomputed_grid_change"]["outlet_velocity_relative"],
            velocity_change,
        )
        self.assertEqual(self.openfoam_audit["verified_raw_artifact_count"], 24)
        self.assertTrue(self.openfoam["numerical_gates"]["all_cases_converged"])
        self.assertFalse(
            self.openfoam["numerical_gates"][
                "bulk_total_pressure_drop_grid_change_below_10_percent"
            ]
        )
        self.assertFalse(self.openfoam_audit["release_authorized"])
        self.assertTrue(all(not value for value in self.openfoam["engineering_gates"].values()))

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
        self.assertEqual(self.simready["agent_sanitization"]["remaining_forbidden_properties"], [])
        self.assertEqual(self.simready["physicsnemo_runtime_smoke"]["scope"],
                         "GPU tensor runtime only; no surrogate trained and no physical validation")
        gates = self.simready["gates"]
        self.assertTrue(gates["simready_isolated_asset_passed"])
        self.assertFalse(gates["omniverse_exhaust_assembly_function_tested"])
        self.assertFalse(gates["manufacturing_authorized"])
        still = self.simready["public_media"]["still"]
        self.assertEqual(still["sha256"], digest(SIMREADY / still["path"]))
        overlay = self.simready["grasp_annotation"]["overlay"]
        self.assertEqual(overlay["sha256"], digest(SIMREADY / overlay["path"]))

    def test_omniverse_build_screen_is_hash_bound_and_fail_closed(self) -> None:
        scene = self.build_screen
        build = scene["build_scene"]
        self.assertEqual(build["orientation"], "roll_y_25")
        self.assertEqual(build["machine_envelope_mm"], {"width": 250.0, "depth": 250.0, "height": 325.0})
        self.assertTrue(build["candidate_grounded_on_plate"])
        self.assertTrue(build["bare_part_inside_nominal_machine_envelope"])
        self.assertGreater(
            scene["build_scene"]["conservative_candidate_world_bounds_mm"]["size"][2],
            scene["build_scene"]["slice_geometry_build_height_mm"],
        )
        for status in scene["validators"].values():
            self.assertEqual(status, "PASS")
        image = scene["render"]["image"]
        self.assertEqual(image["sha256"], digest(LPBF / image["path"]))
        self.assertTrue(scene["render"]["flattened_for_render_only"])
        self.assertTrue(scene["render"]["visually_inspected"])
        self.assertFalse(scene["gates"]["distortion_field_applied"])
        self.assertFalse(scene["gates"]["recoater_collision_validated"])
        self.assertFalse(scene["gates"]["omniverse_exhaust_assembly_function_tested"])
        self.assertFalse(scene["gates"]["metal_print_authorized"])


if __name__ == "__main__":
    unittest.main()
