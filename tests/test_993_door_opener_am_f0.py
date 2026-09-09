import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-INT-DOOR-OPENER-LEVER-F0-0001"
TWIN_ID = "TWIN-993-DOOR-OPENER-LEVER-ALSI10MG-F0"
PART = ROOT / "parts/993-int-door-opener-lever-f0-0001"
TWIN = ROOT / "twins/993-door-opener-lever-alsi10mg-f0"
EVIDENCE = TWIN / "evidence"
LPBF = EVIDENCE / "lpbf-f0/993-int-door-opener-lever-f0-0001-lpbf-geometry-report.json"
FEA = EVIDENCE / "calculix-f0/calculix-thermomechanical-screen.json"
SIMREADY = EVIDENCE / "simready-f0"
SUMMARY = EVIDENCE / "summary.json"
POLICY = ROOT / "catalog/manufacturing/am-validation-policy.json"
PROCESS = ROOT / "catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json"
TWIN_RECORD = ROOT / "catalog/twins/twin-993-door-opener-lever-alsi10mg-f0.json"
RUNNER = TWIN / "source/run_calculix_thermomechanical_screen.py"
PUBLISHER = TWIN / "source/publish_evidence_summary.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class DoorOpenerAmF0Tests(unittest.TestCase):
    def test_exact_eos_route_remains_coupon_screening(self) -> None:
        process = load(PROCESS)
        self.assertEqual(process["system"], "EOS M 290")
        self.assertEqual(process["process_reference"]["layer_thickness_um"], 30.0)
        self.assertEqual(
            process["published_as_manufactured_coupon_properties"]["vertical_yield_strength_mpa"],
            233.0,
        )
        self.assertFalse(process["solver_readiness"]["complete_and_calibrated"])

    def test_master_is_normalized_and_lpbf_screen_is_hash_linked(self) -> None:
        step = PART / "derived/door_opener_lever_f0.step"
        report = load(LPBF)
        self.assertIn("'1970-01-01T00:00:00'", step.read_text(encoding="utf-8")[:400])
        self.assertEqual(report["part_id"], PART_ID)
        self.assertTrue(report["analysis_surface"]["watertight"])
        self.assertTrue(report["analysis_surface"]["single_component"])
        self.assertEqual(report["full_build_slicing"]["layer_count"], 2664)
        self.assertEqual(report["selected_candidate_orientation"], "roll_y_45")
        self.assertAlmostEqual(report["full_build_slicing"]["support_proxy_volume_mm3"], 2714.4975, places=4)
        self.assertEqual(report["thickness_screen"]["p01_mm"], 2.0)
        self.assertEqual(report["powder_escape_screen"]["trapped_void_volume_mm3"], 0.0)
        self.assertFalse(report["gates"]["metal_print_authorized"])

    def test_six_calculix_runs_are_numerically_stable_but_not_release(self) -> None:
        report = load(FEA)
        self.assertEqual(report["twin_id"], TWIN_ID)
        self.assertEqual(report["solver"]["execution_count"], 6)
        self.assertEqual(len(report["cases"]), 3)
        finest = report["cases"][-1]
        self.assertEqual(finest["mesh"]["nodes"], 31666)
        self.assertAlmostEqual(finest["cold_linear_static"]["von_mises_mpa"]["p95"], 45.2270231280366)
        self.assertAlmostEqual(finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"], 46.54628105929385)
        self.assertLess(report["grid_comparison_fine_vs_previous"]["cold_p95_stress_relative_change"], 0.02)
        self.assertLess(report["grid_comparison_fine_vs_previous"]["hot_p95_stress_relative_change"], 0.01)
        self.assertIsNone(report["fatigue_proxy"]["life_prediction"])
        self.assertFalse(report["fatigue_proxy"]["transferable_to_part"])
        self.assertFalse(report["release_authorized"])

    def test_minimum_usd_and_current_ov_libraries_pass_without_simready_promotion(self) -> None:
        self.assertEqual(load(SIMREADY / "binary-validation.json"), {"status": "PASS", "rules": []})
        self.assertEqual(load(SIMREADY / "rigid-scene-validation.json"), {"status": "PASS", "rules": []})
        preflight = load(SIMREADY / "preflight.json")
        self.assertEqual(preflight["property_assignment_intent"], "run")
        self.assertEqual(preflight["status"], "blocked_before_content_agents")
        self.assertFalse(preflight["full_simready_profile_passed"])
        rigid = load(SIMREADY / "ovphysx-rigid-screen.json")
        self.assertEqual(rigid["status"], "PASS")
        self.assertEqual(rigid["runtime"]["ovphysx"], "0.5.11")
        self.assertEqual(rigid["runtime"]["ovstage"], "0.1.1.355824")
        self.assertEqual(rigid["synthetic_case"]["final_position_mm"][2], 29.0)
        self.assertFalse(rigid["gates"]["functional_door_assembly"])
        self.assertFalse(rigid["gates"]["manufacturing_release"])

    def test_twin_and_policy_keep_all_interfaces_and_release_blocked(self) -> None:
        twin = load(TWIN_RECORD)
        self.assertEqual(twin["twin_id"], TWIN_ID)
        self.assertTrue(all(interface["status"] == "missing_data" for interface in twin["interfaces"]))
        policy = load(POLICY)
        stages = policy["part_overrides"][PART_ID]["stages"]
        self.assertEqual(set(stages), {row["stage_id"] for row in policy["stage_definitions"]})
        self.assertEqual(stages["02_cad_brep_and_mesh_integrity"]["status"], "passed")
        self.assertEqual(stages["03_full_layer_slicing_and_supports"]["status"], "completed_screening")
        self.assertEqual(stages["08_omniverse_simready_asset"]["status"], "completed_screening")
        self.assertEqual(stages["09_omniverse_assembly_function"]["status"], "blocked_missing_input")
        self.assertEqual(stages["11_engineering_release"]["status"], "blocked_missing_input")

    def test_summary_is_reproducible_and_documents_the_executed_stack(self) -> None:
        committed = load(SUMMARY)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"
            subprocess.run(
                [sys.executable, str(PUBLISHER), "--project-root", str(ROOT), "--output", str(output)],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            rebuilt = load(output)
        self.assertEqual(rebuilt, committed)
        self.assertEqual(committed["status"], "virtual_screen_complete_full_simready_and_release_blocked")
        self.assertEqual(committed["executed_stack"]["cad_to_usd"]["validation"], "usd-validation-nvidia 1.21.0")
        self.assertFalse(committed["gates"]["full_simready_profile_for_this_revision"])
        self.assertFalse(committed["gates"]["manufacturing_release"])

    def test_equation_helpers_are_deterministic(self) -> None:
        spec = importlib.util.spec_from_file_location("door_calculix", RUNNER)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertAlmostEqual(module.relative_change(10.0, 9.5), 0.05)
        goodman = module.goodman_screen(10.0)
        self.assertFalse(goodman["transferable_to_part"])
        self.assertIsNone(goodman["life_prediction"])


if __name__ == "__main__":
    unittest.main()
