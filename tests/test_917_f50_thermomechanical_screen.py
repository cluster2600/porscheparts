#!/usr/bin/env python3
"""Tests fail-closed du criblage thermo-mécanique F50."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "twins/reference-917-engine"
CONTRACT = BASE / "thermomechanical-screen-f50.json"
RUNNER = BASE / "source/run_f50_thermomechanical_screen.py"
EVIDENCE = BASE / "evidence/f50-thermomechanical"
REPORT = EVIDENCE / "thermomechanical-screen-report.json"
MANIFEST = EVIDENCE / "manifest.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F50ThermomechanicalScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load(CONTRACT)
        cls.report = load(REPORT)
        cls.manifest = load(MANIFEST)

    def test_canonical_verifier_passes(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "verify",
                "--root",
                str(ROOT),
                "--contract",
                str(CONTRACT),
                "--evidence",
                str(EVIDENCE),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('"release_gates_closed": true', completed.stdout)
        self.assertIn('"skin_untouched": true', completed.stdout)

    def test_upstream_hashes_and_complete_traces_are_locked(self) -> None:
        for binding in self.contract["upstream"].values():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path), binding["sha256"])
        expected = {
            "2v": "2v-cantera_finite_rate-cd0.72-dca0.25",
            "4v": "4v-cantera_finite_rate-cd0.72-dca0.25",
        }
        for variant, case_id in expected.items():
            binding = self.contract["variants"][variant]["trace"]
            self.assertEqual(binding["case_id"], case_id)
            self.assertEqual(sha256(ROOT / binding["path"]), binding["sha256"])
        self.assertIn("one complete F46 trace", self.contract["load_policy"]["trace_selection"])

    def test_no_external_shape_or_scale_was_created(self) -> None:
        geometry = self.contract["geometry_policy"]
        self.assertEqual(geometry["modelled_domain"], "local_circular_combustion_deck_witness_only")
        self.assertEqual(geometry["bore_shape"], "circle")
        self.assertFalse(geometry["full_head_or_external_skin_modelled"])
        self.assertFalse(geometry["F43_external_skin_loaded_or_modified"])
        self.assertFalse(geometry["F43_external_skin_approximated"])
        self.assertFalse(geometry["global_oval_or_ellipse_created"])
        self.assertFalse(geometry["anisotropic_scaling_used"])
        scope = self.report["scope"]
        self.assertFalse(scope["F43_external_skin_loaded_modified_or_approximated"])
        self.assertFalse(scope["global_oval_or_ellipse_created"])
        self.assertFalse(scope["anisotropic_scaling_used"])

    def test_six_real_mesh_cases_and_fields_are_reported(self) -> None:
        cases = self.report["cases"]
        self.assertEqual(len(cases), 6)
        by_variant = {"2v": [], "4v": []}
        for case in cases:
            by_variant[case["variant"]].append(case)
            self.assertEqual(case["classification"], "executed_local_circular_deck_witness_not_full_head")
            self.assertGreater(case["mesh"]["tetrahedra_C3D4"], 3000)
            self.assertGreater(case["mesh"]["minimum_signed_volume_mm3"], 0.0)
            self.assertGreaterEqual(case["mesh"]["minimum_mean_ratio"], 0.05)
            self.assertTrue(all(case["numerical_gates"].values()))
            self.assertGreater(case["thermal_results"]["temperature_maximum_c"], 80.0)
            self.assertLess(case["thermal_results"]["heat_balance"]["relative_imbalance"], 0.02)
            for mode in ("pressure_only", "thermo_pressure"):
                solver = case["structural"][mode]["solver"]
                self.assertEqual(solver["return_code"], 0)
                self.assertTrue(solver["job_finished_marker"])
                results = case["structural"][mode]["results"]
                self.assertEqual(results["stress_sample_count"], case["mesh"]["tetrahedra_C3D4"])
                self.assertEqual(results["displacement_sample_count"], case["mesh"]["nodes"])
        self.assertEqual(sorted(item["mesh_target_size_mm"] for item in by_variant["2v"]), [2.5, 3.5, 5.0])
        self.assertEqual(sorted(item["mesh_target_size_mm"] for item in by_variant["4v"]), [2.5, 3.5, 5.0])

    def test_convergence_passes_but_engineering_screen_stays_red(self) -> None:
        for variant in ("2v", "4v"):
            self.assertTrue(all(self.report["finest_pair_convergence"][variant]["gates"].values()))
        gates = self.report["gates"]
        self.assertTrue(gates["all_six_mesh_cases_pass_local_numerical_gates"])
        self.assertTrue(gates["both_variants_pass_finest_pair_convergence"])
        self.assertTrue(gates["local_witness_numerical_screen_passed"])
        self.assertFalse(gates["both_variants_below_300C_screen_limit"])
        self.assertFalse(gates["both_variants_below_CP1_room_temperature_yield_p95"])
        self.assertFalse(gates["local_witness_engineering_screen_passed"])
        self.assertIn("engineering_screen_failed", self.report["status"])

    def test_finest_values_and_fatigue_proxy_remain_bounded(self) -> None:
        comparison = self.report["finest_mesh_comparison"]
        temperature = comparison["temperature_maximum_c"]
        stress = comparison["support_excluded_von_mises_p95_mpa"]
        displacement = comparison["maximum_displacement_mm"]
        self.assertAlmostEqual(temperature["2v"], 382.4786, places=3)
        self.assertAlmostEqual(temperature["4v"], 396.6453, places=3)
        self.assertAlmostEqual(stress["2v"], 769.460963859615, places=6)
        self.assertAlmostEqual(stress["4v"], 775.1225096878076, places=6)
        self.assertAlmostEqual(displacement["2v"], 0.19730240871268956, places=9)
        self.assertAlmostEqual(displacement["4v"], 0.18123535635916188, places=9)
        for case in self.report["cases"]:
            fatigue = case["fatigue_proxy"]
            self.assertIsNone(fatigue["cycles_to_failure"])
            self.assertIsNone(fatigue["Miner_damage"])
            self.assertFalse(fatigue["hot_curve_available"])

    def test_release_and_hot_material_gates_are_closed(self) -> None:
        gates = self.report["gates"]
        for name in (
            "room_temperature_yield_reference_is_hot_design_allowable",
            "linear_elastic_response_within_model_validity_screen",
            "full_F43_head_solid_mesh_used",
            "verified_chamber_cooling_and_support_surface_mapping",
            "temperature_dependent_hot_material_card_used",
            "stress_acceptance_against_hot_design_allowable",
            "thermomechanical_fatigue_life_computed",
            "full_head_CHT_completed",
            "physical_correlation_completed",
            "manufacturing_authorized",
            "metal_print_authorized",
            "engine_start_authorized",
        ):
            self.assertFalse(gates[name], name)
        self.assertFalse(self.report["verdict"]["full_head_validated"])
        self.assertFalse(self.report["verdict"]["printable_or_startable_claimed"])

    def test_public_manifest_images_and_no_private_geometry(self) -> None:
        for entry in self.manifest["entries"]:
            path = ROOT / entry["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path), entry["sha256"])
            self.assertEqual(path.stat().st_size, entry["bytes"])
        expected = {
            "f50-local-deck-2v-fields.png": (2720, 986),
            "f50-local-deck-4v-fields.png": (2720, 986),
            "f50-local-deck-mesh-convergence.png": (2550, 935),
        }
        for name, dimensions in expected.items():
            data = (EVIDENCE / name).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), dimensions)
        forbidden = {".step", ".stp", ".stl", ".brep", ".obj", ".msh", ".inp", ".dat", ".frd", ".npz"}
        leaked = [path for path in EVIDENCE.rglob("*") if path.is_file() and path.suffix.lower() in forbidden]
        self.assertEqual(leaked, [])
        publication = self.report["publication"]
        self.assertFalse(publication["private_scan_geometry_published"])
        self.assertFalse(publication["node_coordinates_or_connectivity_published"])
        self.assertFalse(publication["raw_solver_fields_published"])


if __name__ == "__main__":
    unittest.main()
