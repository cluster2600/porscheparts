import hashlib
import importlib.util
import json
import math
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f42-1-thermal-optimization.json"
F42 = ROOT / "twins/reference-917-engine/f42-cooling-cht-contract.json"
SOURCE = ROOT / "twins/reference-917-engine/source/run_f42_1_thermal_optimization.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f42-1-thermal-optimization"
REPORT = EVIDENCE / "f42-1-thermal-optimization-report.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


spec = importlib.util.spec_from_file_location("f42_1", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class F421ThermalOptimizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text())
        cls.f42 = json.loads(F42.read_text())
        cls.report = json.loads(REPORT.read_text())

    def test_exact_F41_provenance_and_no_external_change(self):
        self.assertEqual(self.report["inputs"]["geometry_sha256"], self.contract["inheritance"]["exact_F41_solid_stl_sha256"])
        self.assertFalse(self.report["inputs"]["external_envelope_modified"])
        self.assertTrue(all(not item["external_envelope_modified"] for item in self.report["options"]))

    def test_ten_actual_calculix_cases_and_monotone_h_sweep(self):
        method = self.report["method_a_calculix"]
        self.assertEqual(method["actual_case_count"], 10)
        self.assertTrue(all(item["solver_completed"] for item in method["actual_cases"]))
        cases = sorted((item for item in method["actual_cases"] if item["conductivity_scale"] == 1), key=lambda item: item["external_h_w_m2k"])
        self.assertEqual(len(cases), 8)
        self.assertTrue(all(item["results"]["temperature_samples"] == 99391 for item in cases))
        tmax = [item["results"]["maximum_temperature_c"] for item in cases]
        p95 = [item["results"]["p95_temperature_c"] for item in cases]
        self.assertTrue(all(a > b for a, b in zip(tmax, tmax[1:])))
        self.assertTrue(all(a > b for a, b in zip(p95, p95[1:])))
        self.assertGreater(tmax[-1], 260.0)
        self.assertLess(next(item for item in cases if item["external_h_w_m2k"] == 650)["results"]["p95_temperature_c"], 260.0)

    def test_analytical_anchor_matches_F42(self):
        case = module.analytical_case(self.f42, 0.85, 0.7)
        self.assertAlmostEqual(case["effective_h_w_m2k"], 215.7639414087494, places=8)
        self.assertAlmostEqual(case["straight_channel_pressure_drop_pa"], 1090.6668691481868, places=6)
        self.assertTrue(case["correlation_use_accepted"])

    def test_required_h_area_and_pressure_are_fail_closed(self):
        required = self.report["requirements"]
        self.assertGreater(required["network_required_h_w_m2k"], 1300)
        self.assertGreater(required["network_required_area_multiplier_at_baseline_h"], 6)
        self.assertGreater(required["network_required_airflow_at_capture_100"]["straight_channel_pressure_drop_pa"], 6700)
        self.assertFalse(required["network_required_airflow_at_capture_100"]["correlation_use_accepted"])
        self.assertGreater(required["calculix_fit_required_h_w_m2k"], 3000)
        self.assertTrue(required["calculix_fit_requirement_is_extrapolation"])
        self.assertFalse(required["required_airflow_pressure_estimates_accepted"])

    def test_options_and_cross_method_gates_do_not_claim_validation(self):
        self.assertGreaterEqual(len(self.report["options"]), 3)
        self.assertFalse(self.report["decision"]["any_option_passes_260c_and_6p7kpa"])
        self.assertTrue(self.report["inherited_cross_method_gate"]["h_agreement_below_20_percent"])
        self.assertFalse(self.report["inherited_cross_method_gate"]["pressure_agreement_below_20_percent"])
        for key in ("exact_F41_whole_head_CHT_complete", "exact_F41_OpenFOAM_case_accepted", "material_card_qualified", "physical_validation_complete", "metal_print_authorized", "engine_start_authorized"):
            self.assertFalse(self.report["decision"][key])

    def test_publication_hashes(self):
        manifest = json.loads((EVIDENCE / "publication-manifest.json").read_text())
        self.assertEqual(manifest["report"]["sha256"], sha256(REPORT))
        self.assertEqual(manifest["pareto_csv"]["sha256"], sha256(EVIDENCE / "f42-1-thermal-pareto.csv"))
        self.assertEqual(len(manifest["images"]), 2)
        for item in manifest["images"]:
            self.assertEqual(item["sha256"], sha256(ROOT / item["path"]))
        self.assertFalse(manifest["release_claim"])


if __name__ == "__main__":
    unittest.main()

