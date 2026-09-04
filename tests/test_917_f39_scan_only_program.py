#!/usr/bin/env python3
"""Vérifie que F39 avance sans transformer le scan en métrologie OEM."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/scan-only-program-f39.json"


class F39ScanOnlyProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scan_is_the_only_geometry_source(self) -> None:
        source = self.contract["source_boundary"]
        self.assertFalse(source["additional_dimensions_available"])
        self.assertFalse(source["absolute_scale_measured"])
        self.assertFalse(source["original_porsche_interfaces_measured"])
        self.assertFalse(source["oem_interchangeability_claim_permitted"])
        self.assertEqual(source["scan_unit_convention"], "1 scan unit = 1 mm")

    def test_architecture_is_a_complete_experimental_system(self) -> None:
        design = self.contract["design_intent"]
        self.assertEqual(design["valve_count"], 4)
        self.assertEqual(design["intake_valves"], 2)
        self.assertEqual(design["exhaust_valves"], 2)
        self.assertTrue(design["dual_valve_springs"])
        self.assertTrue(design["oil_galleries"])
        self.assertTrue(design["air_cooling"])

    def test_acceptance_thresholds_are_not_relaxed_from_f38(self) -> None:
        gates = self.contract["fixed_acceptance_criteria"]
        self.assertGreaterEqual(gates["minimum_wall_mm"], 1.5)
        self.assertEqual(gates["trapped_powder_volume_mm3"], 0.0)
        self.assertLessEqual(gates["maximum_inaccessible_support_area_fraction"], 0.005)
        self.assertLessEqual(gates["maximum_bridge_temperature_c"], 260.0)
        self.assertLessEqual(gates["maximum_cross_method_relative_difference"], 0.2)
        self.assertLessEqual(gates["maximum_grid_change_relative"], 0.1)

    def test_virtual_and_physical_release_are_separate(self) -> None:
        matrix = self.contract["verification_matrix"]
        self.assertIn("three-grid whole-head OpenFOAM CHT", matrix["cooling"])
        self.assertIn("Cantera zero-dimensional conservative envelope", matrix["combustion_load"])
        self.assertIn("thermomechanical fatigue", matrix["structure"])
        self.assertIn("inherent-strain distortion", matrix["lpbf"])

    def test_release_is_fail_closed(self) -> None:
        release = self.contract["release_gates"]
        self.assertTrue(release["scan_only_design_basis_locked"])
        for name, value in release.items():
            if name != "scan_only_design_basis_locked":
                self.assertFalse(value, name)


if __name__ == "__main__":
    unittest.main()
