#!/usr/bin/env python3
"""Tests du transfert de chargements F47."""

from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/cae-load-transfer-f47.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f47-cae-loads"
REPORT = EVIDENCE / "load-report.json"
SUMMARY = EVIDENCE / "summary.json"
ENVELOPES = EVIDENCE / "envelopes/f47-load-envelopes.json"
MANIFEST = EVIDENCE / "manifest.json"
SCRIPT = ROOT / "twins/reference-917-engine/source/build_cae_load_transfer_f47.py"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module():
    spec = importlib.util.spec_from_file_location("f47_load_transfer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CaeLoadTransferF47Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load(CONTRACT)
        cls.report = load(REPORT)
        cls.summary = load(SUMMARY)
        cls.envelopes = load(ENVELOPES)
        cls.manifest = load(MANIFEST)

    def test_cli_check_and_all_release_gates_fail_closed(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-root", str(ROOT), "--check"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("F47 CAE load-transfer evidence: OK", result.stdout)
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        self.assertEqual(self.report["release_gates"], self.contract["release_gates"])
        self.assertFalse(self.report["conclusion"]["CFD_or_CHT_or_FEA_executed"])
        self.assertFalse(self.report["quality"]["physical_correlation_completed"])

    def test_upstream_contract_report_manifest_and_every_raw_trace_are_hash_bound(self) -> None:
        upstream = self.contract["upstream"]
        for binding in upstream.values():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file())
            self.assertFalse(path.is_symlink())
            self.assertEqual(sha256(path), binding["sha256"])
        f46_manifest = load(ROOT / upstream["f46_manifest"]["path"])
        f46_artifacts = {item["path"]: item for item in f46_manifest["artifacts"]}
        self.assertEqual(self.report["source_case_count"], 36)
        self.assertEqual(len(self.report["source_case_index"]), 36)
        for case in self.report["source_case_index"]:
            item = f46_artifacts[case["raw_path"]]
            self.assertEqual(case["raw_sha256"], item["sha256"])
            self.assertEqual(sha256(ROOT / case["raw_path"]), item["sha256"])
            self.assertEqual(case["integer_samples_used"], 720)

    def test_exact_matrix_and_no_interpolation(self) -> None:
        cases = self.report["source_case_index"]
        identities = {
            (case["architecture"], case["combustion_model"], case["Cd"], case["crank_step_deg"])
            for case in cases
        }
        expected = {
            (architecture, model, cd, step)
            for architecture in ("2v", "4v")
            for model in ("cantera_finite_rate", "wiebe_counter_model")
            for cd in (0.62, 0.72, 0.82)
            for step in (1.0, 0.5, 0.25)
        }
        self.assertEqual(identities, expected)
        self.assertFalse(self.contract["transfer_grid"]["interpolation_allowed"])
        self.assertTrue(self.report["quality"]["exact_samples_without_interpolation"])
        self.assertEqual(self.summary["envelope_rows_total"], 1440)

    def test_envelopes_are_ordered_complete_and_keep_models_separate(self) -> None:
        variables = self.contract["envelope_policy"]["variables"] + ["pressure_gauge_pa"]
        for architecture in ("2v", "4v"):
            rows = self.envelopes["architectures"][architecture]["rows"]
            self.assertEqual(len(rows), 720)
            self.assertEqual([row["crank_angle_deg"] for row in rows], list(range(720)))
            self.assertAlmostEqual(rows[-1]["cycle_time_s"], 719.0 / 54000.0, places=12)
            for row in rows:
                for variable in variables:
                    cantera = (
                        row[f"cantera_{variable}_min"], row[f"cantera_{variable}_max"]
                    )
                    wiebe = (row[f"wiebe_{variable}_min"], row[f"wiebe_{variable}_max"])
                    outer = (
                        row[f"cross_model_{variable}_min"],
                        row[f"cross_model_{variable}_max"],
                    )
                    self.assertLessEqual(cantera[0], cantera[1])
                    self.assertLessEqual(wiebe[0], wiebe[1])
                    self.assertEqual(outer[0], min(cantera[0], wiebe[0]))
                    self.assertEqual(outer[1], max(cantera[1], wiebe[1]))
                self.assertGreater(row["cross_model_h_gas_w_m2_k_min"], 0.0)
        self.assertFalse(self.envelopes["envelope_policy"]["joint_trajectory_claimed"])

    def test_h_gas_equation_and_flux_closure_reproduce_F46(self) -> None:
        module = load_module()
        mean_piston_speed = 2.0 * 0.0704 * 9000.0 / 60.0
        raw_path = ROOT / next(
            case["raw_path"]
            for case in self.report["source_case_index"]
            if case["case_id"] == "4v-cantera_finite_rate-cd0.72-dca0.25"
        )
        worst = 0.0
        with gzip.open(raw_path, "rt", encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                pressure = float(row["pressure_pa_abs"])
                temperature = float(row["temperature_k"])
                source_flux = float(row["wall_heat_flux_w_m2"])
                coefficient = module.wall_transfer_coefficient(
                    pressure, temperature, mean_piston_speed
                )
                reconstructed = coefficient * (temperature - 475.0)
                worst = max(worst, abs(reconstructed - source_flux) / max(abs(source_flux), 1.0))
        self.assertLessEqual(worst, self.contract["quality_limits"]["relative_wall_flux_closure_limit"])
        self.assertLessEqual(
            worst,
            self.report["quality"]["wall_flux_closure_worst_relative_error"] + 2.0e-12,
        )

    def test_solver_mappings_are_names_only_and_cannot_claim_execution(self) -> None:
        openfoam = load(EVIDENCE / "mappings/openfoam-aate-enginefoam-patches.json")
        calculix = load(EVIDENCE / "mappings/calculix-loads.json")
        for mapping in (openfoam, calculix):
            self.assertFalse(mapping["execution_claimed"])
            self.assertFalse(mapping["geometry_loaded"])
            self.assertTrue(all(value is False for value in mapping["release_gates"].values()))
            self.assertFalse(mapping["source_case_policy"]["pointwise_envelope_as_solver_history_allowed"])
            self.assertEqual(mapping["source_case_policy"]["available_case_count"], 36)
        for patch in openfoam["patch_templates"]:
            self.assertIsNone(patch["resolved_geometry_patch"])
            self.assertTrue(patch["status"].startswith("blocked_"))
        for surface_set in calculix["required_surface_sets"]:
            self.assertTrue(any(value is None for value in surface_set.values()))
            self.assertTrue(surface_set["status"].startswith("blocked_"))
        self.assertFalse(calculix["thermal"]["simultaneous_Robin_and_direct_flux_allowed"])

    def test_geometry_policy_forbids_any_authored_shape(self) -> None:
        policy = self.contract["geometry_policy"]
        self.assertFalse(policy["geometry_created"])
        self.assertFalse(policy["cad_created"])
        self.assertFalse(policy["mesh_created"])
        self.assertFalse(policy["external_scan_contour_modified"])
        self.assertFalse(policy["oval_or_ellipse_created"])
        self.assertTrue(policy["patches_are_unresolved_names_only"])
        for path in EVIDENCE.rglob("*"):
            if path.is_file():
                self.assertNotIn(path.suffix.lower(), {".step", ".stp", ".stl", ".obj", ".msh", ".inp"})

    def test_png_svg_csv_and_manifest_are_complete_and_hash_locked(self) -> None:
        expected = {
            "twins/reference-917-engine/evidence/f47-cae-loads/load-report.json",
            "twins/reference-917-engine/evidence/f47-cae-loads/summary.json",
            "twins/reference-917-engine/evidence/f47-cae-loads/envelopes/f47-load-envelopes.json",
            "twins/reference-917-engine/evidence/f47-cae-loads/envelopes/f47-2v-load-envelope.csv",
            "twins/reference-917-engine/evidence/f47-cae-loads/envelopes/f47-4v-load-envelope.csv",
            "twins/reference-917-engine/evidence/f47-cae-loads/mappings/openfoam-aate-enginefoam-patches.json",
            "twins/reference-917-engine/evidence/f47-cae-loads/mappings/calculix-loads.json",
            "twins/reference-917-engine/evidence/f47-cae-loads/figures/f47-cae-load-envelopes.svg",
            "twins/reference-917-engine/evidence/f47-cae-loads/figures/f47-cae-load-envelopes.png",
        }
        artifacts = {item["path"]: item for item in self.manifest["artifacts"]}
        self.assertEqual(set(artifacts), expected)
        self.assertEqual(self.manifest["generator"]["path"], SCRIPT.relative_to(ROOT).as_posix())
        self.assertEqual(self.manifest["generator"]["sha256"], sha256(SCRIPT))
        for rel, item in artifacts.items():
            path = ROOT / rel
            self.assertEqual(path.stat().st_size, item["bytes"])
            self.assertEqual(sha256(path), item["sha256"])
        png = (EVIDENCE / "figures/f47-cae-load-envelopes.png").read_bytes()[:24]
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", png[16:24]), (1920, 1080))
        svg = (EVIDENCE / "figures/f47-cae-load-envelopes.svg").read_text(encoding="utf-8")
        self.assertIn("aucune CFD/CHT/FEA exécutée", svg)
        self.assertIn("Bornes non corrélées", svg)

    def test_validator_rejects_open_gate_geometry_and_joint_envelope_claims(self) -> None:
        module = load_module()
        for mutation in (
            ("release_gates", "engine_start_authorized"),
            ("geometry_policy", "geometry_created"),
            ("geometry_policy", "oval_or_ellipse_created"),
            ("envelope_policy", "joint_trajectory_claimed"),
        ):
            changed = copy.deepcopy(self.contract)
            changed[mutation[0]][mutation[1]] = True
            with self.assertRaises(ValueError):
                module.validate_contract(changed)


if __name__ == "__main__":
    unittest.main()
