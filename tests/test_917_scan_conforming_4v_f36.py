"""Garde-fous de la reconstruction F36 contrainte par le scan."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/scan-conforming-4v-f36.json"
SOURCE = ROOT / "twins/reference-917-engine/source/build_scan_conforming_4v_f36.py"
F34_DOC = ROOT / "docs/917_AIRCOOLED_4V_F34.md"


class ScanConformingFourValveF36Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_f34_product_geometry_is_superseded(self):
        supersedes = self.contract["supersedes"]
        self.assertEqual(supersedes["phase"], "F34")
        self.assertEqual(supersedes["scope"], "product_geometry_only")
        self.assertEqual(supersedes["retained_use"], "numerical_method_regression_only")
        self.assertIn("RETIRÉ", F34_DOC.read_text(encoding="utf-8")[:800])

    def test_exact_scan_is_fail_closed_and_not_published(self):
        source = self.contract["source"]
        self.assertEqual(
            source["sha256"],
            "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486",
        )
        self.assertGreater(source["open_edges"], 90_000)
        self.assertEqual(source["raw_and_derived_geometry_policy"], "local_only_not_committed")
        self.assertFalse(source["porsche_917_dimensional_identity"])
        self.assertFalse(self.contract["reconstruction"]["derived_mesh_committed"])

    def test_four_valve_twin_ignition_architecture_is_explicit(self):
        architecture = self.contract["four_valve_architecture"]
        self.assertEqual(architecture["intake"]["count"], 2)
        self.assertEqual(architecture["exhaust"]["count"], 2)
        self.assertEqual(architecture["ignition"]["count"], 2)
        self.assertFalse(architecture["spring_package"]["rate_and_installed_load_released"])

    def test_scan_conformance_and_wall_screen_are_quantified(self):
        reconstruction = self.contract["reconstruction"]
        self.assertTrue(reconstruction["watertight"])
        self.assertEqual(reconstruction["body_count"], 1)
        self.assertLess(reconstruction["scan_to_reconstruction_p95_obj_units"], 0.5)
        wall = self.contract["internal_wall_screen"]
        self.assertGreater(wall["minimum_obj_units"], 6.0)
        self.assertFalse(wall["ct_or_metrology_validation"])

    def test_new_geometry_builder_verifies_source_and_keeps_scale_qualified(self):
        source_text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("EXPECTED_SCAN_SHA256", source_text)
        self.assertIn("screened_poisson", source_text)
        self.assertIn("echelle physique non confirmee", source_text)
        self.assertIn('"human_morphology_review": False', source_text)

    def test_f34_cfd_is_not_reused_and_all_release_gates_are_closed(self):
        cooling = self.contract["cooling_model_next_gate"]
        self.assertEqual(cooling["method_a"], "OpenFOAM_finite_volume_RANS_CHT")
        self.assertIn("FluidX3D", cooling["method_b"])
        self.assertFalse(cooling["f34_results_reusable_as_f36_performance_evidence"])
        gates = self.contract["engineering_gates"]
        self.assertFalse(gates["human_morphology_review"])
        self.assertTrue(all(value is False for key, value in gates.items() if key != "automated_surface_conformance"))


if __name__ == "__main__":
    unittest.main()
