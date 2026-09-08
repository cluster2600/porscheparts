import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART_ID = "993-ELEC-HEADLAMP-SPRING-HOOK-F0-0001"
TWIN_ID = "TWIN-993-HEADLAMP-SPRING-HOOK-ALSI10MG-F0"
EVIDENCE = ROOT / "twins/993-headlamp-spring-hook-alsi10mg-f0/evidence"
LPBF = EVIDENCE / "lpbf-f0/993-elec-headlamp-spring-hook-f0-0001-lpbf-geometry-report.json"
FEA = EVIDENCE / "calculix-f0/calculix-thermomechanical-screen.json"
SUMMARY = EVIDENCE / "summary.json"
SIMREADY = EVIDENCE / "simready-f0"
POLICY = ROOT / "catalog/manufacturing/am-validation-policy.json"
PROCESS = ROOT / "catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json"
SOURCE = ROOT / "catalog/sources/src-eos-alsi10mg-m290-30um.json"
RUNNER = ROOT / "twins/993-headlamp-spring-hook-alsi10mg-f0/source/run_calculix_thermomechanical_screen.py"
PUBLISHER = ROOT / "twins/993-headlamp-spring-hook-alsi10mg-f0/source/publish_evidence_summary.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class HeadlampHookAmF0Tests(unittest.TestCase):
    def test_exact_eos_route_is_screening_not_an_allowable(self) -> None:
        source = load(SOURCE)
        process = load(PROCESS)
        self.assertEqual(source["source_id"], "SRC-EOS-ALSI10MG-M290-30UM")
        self.assertEqual(process["system"], "EOS M 290")
        self.assertEqual(process["process_reference"]["layer_thickness_um"], 30.0)
        self.assertEqual(process["process_reference"]["technology_readiness_level"], 9)
        self.assertEqual(
            process["published_as_manufactured_coupon_properties"]["vertical_yield_strength_mpa"],
            233.0,
        )
        self.assertFalse(process["solver_readiness"]["complete_and_calibrated"])

    def test_full_layer_geometry_screen_is_hash_linked_and_not_released(self) -> None:
        report = load(LPBF)
        self.assertEqual(report["part_id"], PART_ID)
        self.assertTrue(report["analysis_surface"]["watertight"])
        self.assertTrue(report["analysis_surface"]["single_component"])
        self.assertEqual(report["full_build_slicing"]["layer_count"], 425)
        self.assertEqual(report["selected_candidate_orientation"], "roll_y_45")
        self.assertAlmostEqual(
            report["full_build_slicing"]["support_proxy_volume_mm3"], 3.06, places=6
        )
        self.assertFalse(report["gates"]["metal_print_authorized"])
        self.assertFalse(report["gates"]["target_material_process_physics_correlated"])

    def test_six_calculix_runs_converge_numerically_but_reject_release(self) -> None:
        report = load(FEA)
        self.assertEqual(report["twin_id"], TWIN_ID)
        self.assertEqual(report["solver"]["execution_count"], 6)
        self.assertEqual(len(report["cases"]), 3)
        self.assertEqual(report["cases"][-1]["mesh"]["nodes"], 22415)
        self.assertLess(
            report["grid_comparison_fine_vs_previous"]["cold_p95_stress_relative_change"],
            0.01,
        )
        self.assertLess(
            report["grid_comparison_fine_vs_previous"]["hot_p95_stress_relative_change"],
            0.03,
        )
        hot = report["cases"][-1]["hot_sequential_thermomechanical"]
        self.assertAlmostEqual(hot["von_mises_mpa"]["p95"], 141.8976205984518)
        self.assertGreater(hot["von_mises_mpa"]["maximum"], 300.0)
        self.assertFalse(report["release_authorized"])
        self.assertIsNone(report["selected_variant"])

    def test_nvidia_validation_and_current_ov_libraries_are_executed(self) -> None:
        self.assertEqual(load(SIMREADY / "binary-validation.json"), {"status": "PASS", "rules": []})
        self.assertEqual(
            load(SIMREADY / "rigid-scene-validation.json"),
            {"status": "PASS", "rules": []},
        )
        rigid = load(SIMREADY / "ovphysx-rigid-screen.json")
        self.assertEqual(rigid["status"], "PASS")
        self.assertEqual(rigid["runtime"]["ovphysx"], "0.5.11")
        self.assertEqual(rigid["runtime"]["ovstage"], "0.1.1.355824")
        self.assertEqual(rigid["synthetic_case"]["steps"], 240)
        self.assertEqual(rigid["synthetic_case"]["final_position_mm"][2], 17.0)
        self.assertTrue(rigid["gates"]["software_integration"])
        self.assertFalse(rigid["gates"]["functional_headlamp_assembly"])
        self.assertFalse(rigid["gates"]["manufacturing_release"])

    def test_am_policy_records_every_gate_without_promoting_stage_08(self) -> None:
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
                [
                    sys.executable,
                    str(PUBLISHER),
                    "--project-root",
                    str(ROOT),
                    "--output",
                    str(output),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            rebuilt = load(output)
        self.assertEqual(rebuilt, committed)
        self.assertEqual(committed["status"], "virtual_screen_complete_release_blocked")
        self.assertEqual(committed["executed_stack"]["cad_to_usd"]["validation"], "usd-validation-nvidia 1.21.0")
        self.assertEqual(committed["executed_stack"]["rigid_body"]["ovphysx"], "0.5.11")
        self.assertFalse(committed["gates"]["ovrtx_render_for_this_revision"])
        self.assertFalse(committed["gates"]["manufacturing_release"])

    def test_equation_helpers_are_deterministic(self) -> None:
        spec = importlib.util.spec_from_file_location("hook_calculix", RUNNER)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertAlmostEqual(module.relative_change(10.0, 9.5), 0.05)
        goodman = module.goodman_screen(10.0)
        self.assertFalse(goodman["transferable_to_part"])
        self.assertIsNone(goodman["life_prediction"])


if __name__ == "__main__":
    unittest.main()
