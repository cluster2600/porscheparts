#!/usr/bin/env python3
"""Contrôles fail-closed de l'audit LPBF/structure scan-only F39."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f39-lpbf-scan-only-contract.json"
GENERATOR = ROOT / "twins/reference-917-engine/source/f39-lpbf-scan-only-audit.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f39-lpbf-structural"
REPORT = EVIDENCE / "f39-lpbf-scan-only-report.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class F39LpbfStructuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load(CONTRACT)
        cls.report = load(REPORT)

    def test_report_is_bound_to_contract_generator_and_exact_scan(self) -> None:
        self.assertEqual(self.report["phase"], "F39")
        self.assertEqual(self.report["inputs"]["contract"]["sha256"], sha256(CONTRACT))
        self.assertEqual(self.report["toolchain"]["generator_sha256"], sha256(GENERATOR))
        expected_head = self.contract["source_constraints"]["exact_f37_head_mesh_sha256"]
        self.assertEqual(self.report["inputs"]["exact_f37_head"]["sha256"], expected_head)
        self.assertEqual(expected_head, "3c7159d47be2cd4632ae823a272f73514c784b0659207c002e34c9dc7e49fbbb")

    def test_scan_only_contract_adds_no_part_dimension(self) -> None:
        constraints = self.contract["source_constraints"]
        self.assertFalse(constraints["additional_part_dimensions_introduced"])
        self.assertFalse(constraints["absolute_scale_confirmed"])
        self.assertFalse(constraints["scan_surface_is_production_cad"])
        self.assertTrue(self.report["source_constraints"]["scan_only"])
        self.assertFalse(self.report["source_constraints"]["additional_part_dimensions_introduced"])

    def test_thickness_map_covers_every_scan_triangle_without_overclaim(self) -> None:
        mesh = self.report["scan_mesh"]
        wall = self.report["exhaustive_thickness_map"]
        self.assertEqual(mesh["triangles"], 857330)
        self.assertEqual(wall["triangle_count"], mesh["triangles"])
        self.assertEqual(wall["evaluated_triangle_count"], mesh["triangles"])
        self.assertEqual(wall["resolved_triangle_count"] + wall["unresolved_triangle_count"], mesh["triangles"])
        self.assertEqual(wall["resolved_fraction"], wall["resolved_triangle_count"] / mesh["triangles"])
        self.assertFalse(wall["continuous_surface_proof"])
        self.assertFalse(wall["ct_verified"])
        self.assertFalse(wall["all_resolved_chords_meet_inherited_requirement"])
        self.assertLess(wall["p01_mm_if_scale_is_mm"], wall["inherited_screen_requirement_mm_if_scale_is_mm"])

    def test_local_thickness_map_hash_when_available(self) -> None:
        artifact = self.report["exhaustive_thickness_map"]["local_map"]
        self.assertEqual(artifact["repository_policy"], "local_only_derived_scan_data")
        self.assertTrue(artifact["path"].startswith("local-only://"))
        local = ROOT / "work/917-lpbf-structural-f39" / artifact["path"].removeprefix("local-only://")
        if local.is_file():
            self.assertEqual(local.stat().st_size, artifact["bytes"])
            self.assertEqual(sha256(local), artifact["sha256"])

    def test_void_resolution_study_is_nonzero_nonconverged_and_closed(self) -> None:
        voids = self.report["closed_void_and_powder_escape"]
        results = voids["resolutions"]
        self.assertEqual([item["pitch_mm_if_scale_is_mm"] for item in results], [2.0, 1.5, 1.0])
        self.assertTrue(all(item["trapped_component_count"] > 0 for item in results))
        self.assertTrue(all(not item["all_detected_void_connected_to_exterior"] for item in results))
        self.assertFalse(voids["resolution_converged_below_10_percent"])
        self.assertIsNone(voids["minimum_escape_diameter_mm"])
        self.assertFalse(self.report["gates"]["closed_void_zero_at_all_voxel_resolutions"])
        self.assertFalse(self.report["gates"]["powder_escape_physically_demonstrated"])

    def test_orientation_is_the_recorded_minimum_but_not_machine_slicing(self) -> None:
        screen = self.report["orientation_and_support_screen"]
        eligible = [item for item in screen["candidates"] if item["fits_inherited_250x250x325_envelope_if_scale_is_mm"]]
        expected = min(eligible, key=lambda item: (item["score"], item["id"]))
        self.assertEqual(screen["selected"], expected)
        self.assertEqual(screen["candidate_count"], len(screen["candidates"]))
        self.assertFalse(screen["supports_generated"])
        self.assertFalse(screen["machine_sliced"])
        self.assertFalse(screen["distortion_simulated"])

    def test_allowances_remain_null_without_datums_or_scale(self) -> None:
        allowances = self.report["machining_allowances"]
        self.assertFalse(allowances["numeric_allowances_defined"])
        self.assertGreaterEqual(len(allowances["zones"]), 7)
        self.assertTrue(all(item["additional_allowance_mm"] is None for item in allowances["zones"]))
        self.assertTrue(all(item["datum_defined"] is False for item in allowances["zones"]))

    def test_no_inherent_strain_claim_without_solver_and_calibration(self) -> None:
        simulation = self.report["inherent_strain_simulation"]
        self.assertFalse(simulation["dedicated_additive_layer_activation_solver_available"])
        self.assertFalse(simulation["calibrated_machine_scan_strategy_and_inherent_strain_parameters_available"])
        self.assertFalse(simulation["simulation_executed"])
        self.assertFalse(simulation["uniform_locked_plate_or_free_shrink_promoted_to_process_simulation"])
        self.assertFalse(self.report["gates"]["calibrated_inherent_strain_simulation_complete"])

    def test_carrier_plan_preserves_f38_failure_and_requires_distributed_contact(self) -> None:
        plan = self.report["carrier_distributed_contact_correction_plan"]
        baseline = plan["f38_baseline"]
        self.assertAlmostEqual(baseline["finest_raw_maximum_mpa"], 137.02989655826315)
        self.assertAlmostEqual(baseline["raw_maximum_relative_change"], 0.16539801922564282)
        self.assertFalse(baseline["raw_maximum_converged_below_10_percent"])
        self.assertFalse(baseline["qualified_material_card"])
        self.assertFalse(baseline["nonlinear_contact_complete"])
        self.assertFalse(plan["executed"])
        self.assertIsNone(plan["load_resultants_n"])
        self.assertIsNone(plan["contact_clearances_mm"])
        self.assertIsNone(plan["geometry_corrections_mm"])
        self.assertTrue(any("distributed_tractions" in item for item in plan["implementation_sequence"]))
        self.assertTrue(any("surface_to_surface_contact" in item for item in plan["implementation_sequence"]))

    def test_image_and_release_gates_are_fail_closed(self) -> None:
        image = self.report["published_image"]
        image_path = EVIDENCE / image["path"]
        self.assertTrue(image_path.is_file())
        self.assertEqual(sha256(image_path), image["sha256"])
        safety_gates = (
            "continuous_wall_thickness_proved",
            "powder_escape_physically_demonstrated",
            "support_topology_sliced_and_reviewed",
            "machining_allowances_dimensioned",
            "calibrated_inherent_strain_simulation_complete",
            "carrier_distributed_contact_model_complete",
            "carrier_raw_maximum_converged_below_10_percent",
            "absolute_scale_confirmed",
            "qualified_hot_material_card",
            "ct_cmm_fpi_pressure_test_complete",
            "professional_engineering_review_complete",
            "metal_print_authorized",
            "engine_start_authorized",
        )
        self.assertTrue(all(self.report["gates"][name] is False for name in safety_gates))
        self.assertTrue(all(self.contract["release_gates"][name] is False for name in self.contract["release_gates"]))
        self.assertIn("NON IMPRIMABLE", self.report["verdict"])


if __name__ == "__main__":
    unittest.main()
