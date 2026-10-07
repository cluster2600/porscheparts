import functools
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001"
SCRIPT = PART / "source/cooling_impeller_f1.py"
RECORD = ROOT / "catalog/parts/993-eng-cooling-impeller-we43-f1-0001.json"
REPORT = PART / "evidence/engineering-screen.json"
HOUSING_REPORT = ROOT / "parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json"
SOURCE_PATHS = (
    ROOT / "catalog/sources/src-ornl-we43-lpbf-hyer-2020.json",
    ROOT / "catalog/sources/src-azom-elektron-we43-properties.json",
    ROOT / "catalog/sources/src-apworks-scalmalloy.json",
)
SPEC = importlib.util.spec_from_file_location("cooling_impeller_f1", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


@functools.lru_cache(maxsize=None)
def cached_screen(cad_volume_mm3=None):
    return MODULE.engineering_screen(cad_volume_mm3)


class CoolingImpellerWE43F1Tests(unittest.TestCase):
    def test_duty_is_the_rebuild_rotors_best_efficiency_point(self) -> None:
        duty = MODULE.matched_duty()

        self.assertAlmostEqual(duty["flow_m3_s"], MODULE.SYNTHETIC_AIRFLOW_M3_S, delta=0.005)
        self.assertAlmostEqual(duty["pressure_rise_pa"], MODULE.SYNTHETIC_PRESSURE_RISE_PA, delta=5.0)
        self.assertGreater(duty["flow_m3_s"], duty["stall_onset_flow_m3_s"])
        self.assertAlmostEqual(MODULE.air_density(), 101_325.0 / (287.05 * 353.15))

    def test_f1_keeps_the_rebuild_envelope_and_interfaces(self) -> None:
        rebuild = json.loads(MODULE.REBUILD_PARAMETERS.read_text(encoding="utf-8"))

        self.assertEqual(MODULE.OUTER_DIAMETER_MM, rebuild["rotor_diameter_mm"])
        self.assertEqual(MODULE.HUB_OUTER_DIAMETER_MM, 2 * rebuild["cup_radius_mm"])
        self.assertEqual(MODULE.CUP_DEPTH_MM, rebuild["cup_rear_z_mm"] - rebuild["cup_front_z_mm"])
        self.assertEqual(MODULE.BLADE_COUNT, rebuild["blade_count"])
        self.assertEqual(MODULE.VENT_COUNT, rebuild["vent_count"])
        self.assertEqual(MODULE.HUB_BORE_DIAMETER_MM, 2 * rebuild["bore_radius_mm"])
        self.assertFalse(MODULE.SHROUDED)
        reference = MODULE.design_reference_rotor()
        self.assertEqual(reference["blade_pitch_from_rotation_plane_deg"], rebuild["blade_pitch_deg"])
        for section in reference["sections"]:
            self.assertAlmostEqual(section["stagger_deg"], 90.0 - rebuild["blade_pitch_deg"])

    def test_operating_points_sit_on_the_system_curve(self) -> None:
        screen = cached_screen()
        k = MODULE.system_coefficient()
        for point in screen["operating_points"].values():
            self.assertAlmostEqual(point["useful_pressure_pa"], k * point["flow_m3_s"] ** 2, delta=0.5)
            self.assertEqual(point["stalled_station_count"], 0)

    def test_f1_moves_more_air_than_the_rebuild_on_the_same_power(self) -> None:
        screen = cached_screen()
        results = screen["results"]

        self.assertGreater(results["f1_flow_gain_vs_rebuild"], 0.0)
        self.assertLess(abs(results["f1_shaft_power_w"] / results["rebuild_shaft_power_w"] - 1.0), 0.02)
        self.assertGreater(results["f1_flow_gain_at_equal_power_vs_rebuild"], 0.0)
        self.assertGreater(results["f1_with_stator_flow_gain_vs_rebuild"], results["f1_flow_gain_vs_rebuild"])
        self.assertGreater(results["f1_with_stator_flow_gain_at_equal_power_vs_rebuild"], 0.05)
        margins = results["stall_margins"]
        self.assertGreaterEqual(margins[MODULE.F1_ROTOR], margins[MODULE.REFERENCE] - 0.01)
        for row in screen["duty_sensitivity"]:
            self.assertGreater(row["F1_flow_gain_at_equal_power"], 0.0)
            self.assertEqual(row[MODULE.F1_ROTOR]["stalled_station_count"], 0)
        for row in screen["rebuild_pitch_sensitivity"]:
            self.assertGreater(row["F1_flow_gain_at_equal_power_vs_rebuild"], 0.0)

    def test_radial_equilibrium_carries_the_flow_and_balances_a_free_vortex(self) -> None:
        radii = MODULE.stations(82.5, 122.5)
        rho = MODULE.air_density()
        omega = MODULE.angular_speed(10_000.0)
        swirl = 2.0
        free = MODULE.radial_equilibrium(
            radii, 30.0, rho,
            lambda i, cx: swirl / radii[i],
            lambda i, cx, cu: rho * omega * radii[i] * cu,
        )
        for c_x2 in free["axial_m_s"]:
            self.assertAlmostEqual(c_x2, 30.0, places=4)
        forced = MODULE.radial_equilibrium(
            radii, 30.0, rho,
            lambda i, cx: 20.0,
            lambda i, cx, cu: rho * omega * radii[i] * cu,
        )
        self.assertAlmostEqual(sum(forced["axial_m_s"]) / len(radii), 30.0, places=4)
        self.assertLess(forced["axial_m_s"][0], 30.0)
        self.assertGreater(forced["axial_m_s"][-1], 30.0)
        self.assertEqual(forced["collapsed_station_count"], 0)

    def test_hub_section_clears_the_de_haller_guideline(self) -> None:
        design = MODULE.design_f1_rotor()
        self.assertEqual(MODULE.VORTEX_EXPONENT, 1.0)
        self.assertEqual(design["design_exit_collapsed_station_count"], 0)
        self.assertGreaterEqual(cached_screen()["results"]["f1_minimum_de_haller_ratio"], 0.72)
        for section in design["sections"]:
            self.assertAlmostEqual(section["axial_velocity_ratio"], 1.0, places=4)
        for point in cached_screen()["operating_points"].values():
            self.assertEqual(point["exit_collapsed_station_count"], 0)
            self.assertGreater(point["stall_margin"], 0.0)

    def test_flow_scales_linearly_with_speed(self) -> None:
        sweep = cached_screen()["speed_sweep"]
        at_10k = next(p for p in sweep if p["speed_rpm"] == 10000.0)
        for p in sweep:
            ratio = p["speed_rpm"] / 10000.0
            self.assertAlmostEqual(
                p["F1_rotor_flow_m3_s"], at_10k["F1_rotor_flow_m3_s"] * ratio, places=3
            )

    def test_carter_deviation_is_inverted_exactly(self) -> None:
        kappa1, kappa2 = MODULE.metal_angles(60.0, 40.0, 1.0)
        row = MODULE.cascade(60.0, kappa1, kappa2, 1.0)
        self.assertAlmostEqual(row["beta2_deg"], 40.0, places=6)
        self.assertAlmostEqual(row["incidence_deg"], 0.0)

    def test_fits_housing_throat_and_print_plate(self) -> None:
        housing = json.loads(HOUSING_REPORT.read_text(encoding="utf-8"))
        integration = cached_screen()["upstream_f0_integration"]

        self.assertEqual(integration["housing_part_id"], housing["part_id"])
        self.assertAlmostEqual(integration["radial_clearance_mm"], 3.5)
        self.assertTrue(integration["housing_fit_screen_pass"])
        self.assertTrue(integration["fits_eos_m290_flat"])

    def test_we43_is_lighter_and_passes_centrifugal_and_modal_screens(self) -> None:
        screen = cached_screen()
        materials = screen["material_screens"]
        we43 = materials["WE43_LPBF_T6"]["results"]
        alsi = materials["AlSi10Mg_LPBF_T6"]["results"]

        self.assertAlmostEqual(we43["analytical_mass_g"] / alsi["analytical_mass_g"], 1840.0 / 2670.0)
        self.assertIsNone(we43["overspeed_shroud_hoop_stress_mpa"])
        self.assertGreater(we43["overspeed_blade_root_aero_bending_mpa"], 0.0)
        self.assertTrue(we43["centrifugal_screen_pass"])
        self.assertTrue(we43["modal_screen_pass"])
        self.assertFalse(we43["constrained_thermal_screen_pass"])
        self.assertEqual(we43["governing_blade_mode_hz"], we43["blade_first_mode_cantilever_hz"])
        self.assertGreater(we43["governing_blade_mode_hz"], 1.2 * we43["spoke_order_hz"])
        self.assertGreaterEqual(we43["yield_to_hub_rim_ratio"], MODULE.MINIMUM_SCREEN_RATIO)
        self.assertGreaterEqual(we43["yield_to_hub_bore_ratio"], MODULE.MINIMUM_SCREEN_RATIO)

    def test_committed_step_sources_and_catalogue_are_fail_closed(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(record["manufacturing"]["preferred_process"], "LPBF")
        self.assertEqual(report["step_roundtrip"]["status"], "passed")
        self.assertEqual(report["step_roundtrip"]["solid_count"], 1)
        self.assertEqual(report["step_roundtrip"]["blade_count"], 11)
        envelope = report["step_roundtrip"]["envelope_mm"]
        self.assertLessEqual(max(envelope[:2]), MODULE.OUTER_DIAMETER_MM + 1e-6)
        self.assertGreater(min(envelope[:2]), MODULE.OUTER_DIAMETER_MM - 3.0)
        self.assertAlmostEqual(envelope[2], MODULE.CUP_DEPTH_MM, places=3)
        self.assertLess(report["mass"]["volume_ratio_f1_to_rebuild"], 1.0)
        self.assertEqual(report["results"], {**cached_screen(report["results"]["cad_volume_mm3"])["results"]})
        for path in SOURCE_PATHS:
            source = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn(source["source_id"], json.dumps(MODULE.MATERIALS) + record["provenance"]["sources"].__repr__())
        self.assertGreaterEqual(len(report["release_blockers"]), 8)
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_operation_authorized"])
        self.assertFalse(report["release_authorized"])


if __name__ == "__main__":
    unittest.main()
