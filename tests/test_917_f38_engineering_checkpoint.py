#!/usr/bin/env python3
"""Contrôles du paquet intégré F38 publié en mode fail-closed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f38-engineering-checkpoint"
REPORT = EVIDENCE / "f38-engineering-checkpoint.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F38EngineeringCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_rejected_box_geometry_is_not_claimed(self) -> None:
        geometry = self.report["geometry"]
        self.assertTrue(geometry["scan_morphology_preserved"])
        self.assertTrue(geometry["boxy_prototype_rejected"])
        self.assertFalse(geometry["production_brep_complete"])

    def test_geometry_and_lpbf_failures_are_preserved(self) -> None:
        geometry = self.report["geometry"]
        self.assertLess(geometry["minimum_wall_mm"], geometry["minimum_wall_requirement_mm"])
        self.assertGreater(geometry["trapped_void_volume_mm3_at_1_mm"], 0)
        self.assertFalse(geometry["void_study_converged"])
        self.assertGreater(geometry["support_area_fraction"], 0.005)
        self.assertFalse(geometry["gmsh_volume_mesh_success"])

    def test_four_valve_bundle_is_explicit_and_conditional(self) -> None:
        valvetrain = self.report["valvetrain"]
        self.assertEqual(valvetrain["valves"], 4)
        self.assertEqual(valvetrain["guides"], 4)
        self.assertEqual(valvetrain["seats"], 4)
        self.assertEqual(valvetrain["springs"], 8)
        self.assertEqual(valvetrain["total_separate_solids"], 35)
        self.assertFalse(valvetrain["integrated_dimensional_fit_proved"])
        self.assertFalse(valvetrain["structural_proof"])

    def test_structure_is_a_nonconverged_linear_screen(self) -> None:
        structure = self.report["structure"]
        self.assertEqual(structure["mesh_sizes_mm"], [2.0, 1.5, 1.25])
        self.assertTrue(structure["p99_grid_change_below_10_percent"])
        self.assertFalse(structure["raw_maximum_grid_change_below_10_percent"])
        self.assertFalse(structure["nonlinear_contact_complete"])
        self.assertFalse(structure["fatigue_and_thermal_cycle_complete"])

    def test_cooling_has_two_methods_but_rejects_temperature(self) -> None:
        cooling = self.report["cooling"]
        self.assertEqual(cooling["openfoam_cell_counts"], [17280, 138240])
        self.assertLess(cooling["h_relative_difference"], 0.20)
        self.assertGreater(cooling["pressure_drop_relative_difference"], 0.20)
        self.assertGreater(min(cooling["projected_bridge_temperature_range_c"]), 260.0)
        self.assertFalse(cooling["whole_head_cht_complete"])
        self.assertFalse(cooling["temperature_screen_passed"])

    def test_engine_solver_references_are_not_f38_validation(self) -> None:
        boundary = self.report["engine_solver_boundary"]
        self.assertFalse(boundary["exact_ice_engine_foam_executable_executed"])
        self.assertTrue(boundary["generic_xifluid_tutorial_executed"])
        self.assertEqual(boundary["generic_tutorial_valve_count"], 2)
        self.assertFalse(boundary["f38_geometry_coupled"])
        self.assertTrue(boundary["cantera_0d_reference_executed"])
        self.assertFalse(boundary["cantera_coupled_to_f38_cfd"])

    def test_published_artifacts_are_bound_by_hash(self) -> None:
        for name, expected in self.report["artifacts"].items():
            path = EVIDENCE / name
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.stat().st_size, expected["bytes"], name)
            self.assertEqual(sha256(path), expected["sha256"], name)

    def test_release_gates_are_all_closed(self) -> None:
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))
        self.assertEqual(self.report["material"]["coupon_count_planned"], 168)
        self.assertEqual(self.report["material"]["coupon_count_executed"], 0)


if __name__ == "__main__":
    unittest.main()
