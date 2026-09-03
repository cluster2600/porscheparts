"""Preuves fail-closed du chemin moteur OpenFOAM F37."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f37-ice-engine-foam"
REPORT = EVIDENCE / "report.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F37IceEngineFoamEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_compact_logs_are_hash_bound_and_terminal(self):
        for name, digest in self.report["published_evidence"].items():
            self.assertEqual(sha256(EVIDENCE / name), digest, name)

        solver_log = (EVIDENCE / "log.foamRun.excerpt.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("Selecting solver XiFluid", solver_log)
        self.assertIn("Selecting fvMeshMover multiValveEngine", solver_log)
        self.assertIn("Mapping to mesh time 100", solver_log)
        self.assertIn("Time = 110CAD", solver_log)
        self.assertIn("Mesh OK.", solver_log)
        self.assertNotIn("FOAM FATAL", solver_log)
        self.assertNotIn("Command exited with non-zero", solver_log)

    def test_requested_binary_is_not_silently_substituted(self):
        probe = self.report["requested_solver_probe"]
        self.assertEqual(probe["requested_label"], "iceEngineFoam")
        for key in (
            "iceEngineFoam_executable_present",
            "engineFoam_executable_present",
            "XiEngineFoam_executable_present",
            "coldEngineFoam_executable_present",
        ):
            self.assertFalse(probe[key])
        self.assertFalse(probe["substitution_claimed"])

    def test_executed_case_is_only_the_generic_reference(self):
        case = self.report["executed_reference_case"]
        self.assertEqual(case["solver_module"], "XiFluid")
        self.assertEqual(case["spatial_dimension"], "2D")
        self.assertEqual(case["valve_count"], 2)
        self.assertFalse(case["f37_geometry_used"])
        self.assertFalse(case["porsche_917_geometry_used"])
        self.assertFalse(case["cantera_coupled_to_case"])
        self.assertEqual(case["solver_exit_codes"], [0, 0])
        self.assertTrue(case["topology_change_at_100_cad"]["observed"])
        self.assertTrue(case["final_state_at_110_cad"]["mesh_ok"])

    def test_cantera_is_load_only_and_release_gates_remain_closed(self):
        cantera = self.report["cantera_load_boundary"]
        self.assertEqual(
            sha256(ROOT / "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json"),
            cantera["source_report_sha256"],
        )
        self.assertEqual(
            sha256(ROOT / "twins/reference-917-engine/evidence/f34/report.json"),
            cantera["cross_method_report_sha256"],
        )
        self.assertEqual(
            cantera["use_in_f37_program"],
            "downstream_conservative_structural_load_only",
        )
        self.assertFalse(cantera["pressure_cross_method_passed"])
        self.assertFalse(cantera["injected_into_reference_engine_tutorial"])
        self.assertFalse(cantera["combustion_or_power_validation_claimed"])

        gates = self.report["gates"]
        self.assertTrue(gates["reference_engine_solver_path_executed"])
        self.assertTrue(gates["reference_dynamic_mesh_topology_change_executed"])
        self.assertFalse(gates["exact_iceEngineFoam_executable_executed"])
        self.assertFalse(gates["f37_four_valve_moving_mesh_executed"])
        self.assertFalse(gates["f37_combustion_executed"])
        self.assertFalse(gates["physical_correlation_complete"])
        self.assertFalse(gates["metal_print_authorized"])
        self.assertFalse(gates["engine_start_authorized"])

    def test_no_raw_scan_or_engine_mesh_is_published(self):
        forbidden = {".obj", ".ply", ".stl", ".3mf", ".foam"}
        self.assertFalse(
            [path.name for path in EVIDENCE.iterdir() if path.suffix.lower() in forbidden]
        )


if __name__ == "__main__":
    unittest.main()
