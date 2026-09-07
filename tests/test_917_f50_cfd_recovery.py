#!/usr/bin/env python3
"""Contrôles autonomes des preuves publiques de récupération CFD F50."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f50-cfd-recovery-contract.json"
STEADY_CONTRACT = ROOT / "twins/reference-917-engine/f50-steady-cfd-contract.json"
F48_REPORT = ROOT / "twins/reference-917-engine/evidence/f48-cfd-domains/f48-cfd-domain-report.json"
F49_CONTRACT = ROOT / "twins/reference-917-engine/f49-cfd-cht-contract.json"
F49_REPORT = ROOT / "twins/reference-917-engine/evidence/f49-cfd-cht/f49-cfd-cht-report.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f50-cfd-recovery"
REPORT = EVIDENCE / "f50-cfd-recovery-report.json"
PUBLICATION = EVIDENCE / "publication.json"
SOURCES = (
    ROOT / "twins/reference-917-engine/source/diagnose_cfd_recovery_f50.py",
    ROOT / "twins/reference-917-engine/source/build_cfd_cases_f50_steady.py",
    ROOT / "twins/reference-917-engine/source/run_cfd_cases_f50_steady.py",
    ROOT / "twins/reference-917-engine/source/build_cfd_cases_f50_incompressible.py",
    ROOT / "twins/reference-917-engine/source/run_cfd_cases_f50_incompressible.py",
    ROOT / "twins/reference-917-engine/source/publish_cfd_recovery_f50.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F50CFDRecoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.steady_contract = json.loads(STEADY_CONTRACT.read_text(encoding="utf-8"))
        cls.f48 = json.loads(F48_REPORT.read_text(encoding="utf-8"))
        cls.f49_contract = json.loads(F49_CONTRACT.read_text(encoding="utf-8"))
        cls.f49 = json.loads(F49_REPORT.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.publication = json.loads(PUBLICATION.read_text(encoding="utf-8"))

    def test_contract_has_two_independent_steady_attempts_and_strict_gates(self) -> None:
        attempts = self.contract["attempts"]
        self.assertEqual(attempts["F50_steady_compressible"]["solver"], "foamRun -solver fluid")
        self.assertTrue(attempts["F50_steady_compressible"]["energy_equation"])
        self.assertEqual(attempts["F50_steady_incompressible"]["solver"], "foamRun -solver incompressibleFluid")
        self.assertFalse(attempts["F50_steady_incompressible"]["energy_equation"])
        gates = self.contract["strict_gates"]
        self.assertEqual(gates["mass_imbalance_percent_at_most"], 1.0)
        self.assertEqual(gates["energy_imbalance_percent_at_most"], 1.0)
        self.assertEqual(gates["sink_mass_flow_tail_spread_percent_at_most"], 1.0)
        self.assertEqual(gates["three_grid_GCI"]["safety_factor"], 1.25)
        self.assertFalse(self.contract["fail_closed"]["incompressible_flow_can_open_energy_gate"])

    def test_exact_twelve_case_matrix_and_F48_source_hashes(self) -> None:
        expected = {
            f"{variant.lower()}-{level}-{screen}"
            for variant in ("2V", "4V")
            for level in ("coarse", "medium", "fine")
            for screen in ("intake", "exhaust")
        }
        self.assertEqual(self.report["case_count"], 12)
        self.assertEqual(set(self.report["case_index"]), expected)
        for case_id, case in self.report["case_index"].items():
            variant, level, _screen = case_id.split("-")
            f48 = self.f48["gas_domains"][variant.upper()][level]
            self.assertEqual(case["source_mesh_sha256"], f48["msh_sha256"])
            self.assertEqual(case["F48_native_tetrahedron_count"], f48["tetrahedron_count"])
            self.assertFalse(case["case_validation_gate_pass"])
            self.assertFalse(case["energy_gate_applicable"])

    def test_stale_builder_execution_status_is_normalized_from_solver_evidence(self) -> None:
        self.assertIn("legacy_execution_status", self.report["normalizations"])
        for case in self.report["case_index"].values():
            self.assertEqual(case["legacy_input_execution_status"], "prepared_not_run")
            self.assertEqual(case["execution_status"], "EXECUTED")
            self.assertGreater(case["solver_step"]["elapsed_s"], 0.0)
            self.assertEqual(len(case["solver_step"]["log_sha256"]), 64)

    def test_density_and_physical_pressure_difference_match_F49(self) -> None:
        for case in self.report["case_index"].values():
            screen = self.f49_contract["openfoam"]["screens"][case["screen"]]
            expected_rho = screen["source_total_pressure_pa_abs"] / (287.05 * screen["source_temperature_k"])
            self.assertTrue(math.isclose(case["source_density_kg_m3"], expected_rho, rel_tol=1e-12))
            self.assertEqual(case["imposed_physical_pressure_difference_pa"], 10000.0)

    def test_time_step_collapse_is_diagnosed_not_called_convergence(self) -> None:
        diagnostic = self.report["diagnostic"]["summary"]
        for case_id, record in diagnostic["transient_F49"].items():
            expected = self.f49["failed_full_horizon_exhaust_reruns"][case_id]
            self.assertEqual(record["minimum_time_step_s"], expected["minimum_time_step_s"])
            self.assertLess(record["final_physical_time_s"], 0.005)
            self.assertGreater(record["local_convective_rate_growth_lower_bound_from_dt_ratio"], 1e30)
            self.assertFalse(record["physical_cause_established"])
            self.assertFalse(record["validation_claim"])
        steady = diagnostic["steady_compressible_F50"]
        self.assertFalse(steady["solver_gate_pass"])
        self.assertGreater(steady["steady_energy_imbalance_percent_at_failure"], 99.0)
        self.assertGreater(steady["sink_mass_flow_tail_spread_percent_at_failure"], 40.0)

    def test_selected_matrix_compute_provenance_is_explicit(self) -> None:
        provenance = self.report["compute_provenance"]
        self.assertEqual(provenance["transient_diagnostic_site"], "kali")
        self.assertEqual(provenance["steady_compressible_attempt_site"], "kali")
        self.assertEqual(provenance["steady_incompressible_matrix_site"], "vast")
        self.assertEqual(
            provenance["execution_bundle"]["sha256"],
            "c939326b884c75e77de314841503c49c71b96bab38c854dfb7c3156fa5a30c81",
        )
        self.assertTrue(self.report["Vast_used"])
        self.assertEqual(self.publication["incompressible_execution_site"], "vast")

    def test_fail_closed_mesh_GCI_energy_and_cross_method_gates(self) -> None:
        coarse_4v = [
            self.report["case_index"][f"4v-coarse-{screen}"] for screen in ("intake", "exhaust")
        ]
        self.assertTrue(all(not case["gates"]["mesh"] for case in coarse_4v))
        self.assertTrue(all(case["mesh"]["volume_relative_difference_from_F48"] > 0.01 for case in coarse_4v))
        for variant in ("2V", "4V"):
            for screen in ("intake", "exhaust"):
                record = self.report["three_grid_GCI"][variant][screen]
                if not record["pass"]:
                    self.assertNotEqual(record["status"], "GCI_PASS")
        gates = self.report["gates"]
        self.assertFalse(gates["energy_balance_below_1_percent"])
        self.assertFalse(gates["cross_method_agreement_below_5_percent"])
        self.assertFalse(gates["conjugate_CHT_executed"])
        self.assertFalse(gates["manufacturing_authorized"])
        self.assertFalse(gates["engine_start_authorized"])
        self.assertTrue(all(not item["pass"] for item in self.report["cross_method_F49_transient_vs_F50_incompressible"].values()))
        self.assertFalse(self.report["validation_claim"])

    def test_GCI_implementation_passes_a_synthetic_second_order_sequence(self) -> None:
        publisher_path = SOURCES[-1]
        spec = importlib.util.spec_from_file_location("publish_cfd_recovery_f50", publisher_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        synthetic = []
        for level, cells, value in (
            ("coarse", 1000, 1.01),
            ("medium", 8000, 1.0025),
            ("fine", 64000, 1.000625),
        ):
            synthetic.append(
                {
                    "level": level,
                    "F48_native_tetrahedron_count": cells,
                    "values": {"sink_mass_flow_kg_s": value},
                    "flow_numerical_gate_pass": True,
                }
            )
        result = module.gci(synthetic)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["observed_order"], 2.0, places=7)
        self.assertLess(result["GCI_fine_medium_percent"], 1.0)

    def test_no_geometry_operations_or_proxy(self) -> None:
        self.assertFalse(self.report["geometry_modified"])
        self.assertFalse(self.report["ellipse_or_oval_proxy_used"])
        for source in SOURCES:
            tree = ast.parse(source.read_text(encoding="utf-8"))
            calls = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            self.assertTrue(calls.isdisjoint({"addEllipse", "addDisk", "addBox", "importShapes"}), source.name)

    def test_source_and_publication_hashes_are_current(self) -> None:
        for record in self.report["source_artifacts"].values():
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), record["path"])
            self.assertEqual(sha256(path), record["sha256"])
        for record in self.publication["published_files"]:
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), record["path"])
            self.assertEqual(sha256(path), record["sha256"])
        self.assertFalse(self.publication["raw_mesh_or_scan_published"])
        forbidden = {".msh", ".brep", ".step", ".stp", ".stl", ".obj", ".foam"}
        self.assertEqual([path for path in EVIDENCE.rglob("*") if path.is_file() and path.suffix.lower() in forbidden], [])
        for image in self.report["images"].values():
            path = ROOT / image["path"]
            self.assertEqual(path.suffix, ".png")
            self.assertGreater(path.stat().st_size, 20_000)


if __name__ == "__main__":
    unittest.main()
