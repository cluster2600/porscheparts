"""Tests du chargement et des portes fail-closed du calcul tête F38."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/run_f38_head_calculix.py"


class F38HeadCalculixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        ast.parse(cls.source)

    def test_three_mesh_default_and_real_calculix_execution(self):
        self.assertIn('default=[4.0, 3.0, 2.5]', self.source)
        self.assertIn('["ccx", "-i", job.stem]', self.source)
        self.assertIn('gmsh.model.mesh.generate(3)', self.source)

    def test_pressure_and_temperature_are_applied(self):
        self.assertIn('pressure_mpa * area * direction[axis]', self.source)
        self.assertIn('"*CLOAD\\n"', self.source)
        self.assertIn('"*EXPANSION\\n2.2e-5', self.source)
        self.assertIn('temperature = 260.0 - 140.0 * fraction', self.source)

    def test_material_and_release_remain_unqualified(self):
        self.assertIn('"hot_coupon_card_qualified": False', self.source)
        self.assertIn('"thermomechanical_fatigue_complete": False', self.source)
        self.assertIn('"metal_print_authorized": False', self.source)
        self.assertIn('"engine_start_authorized": False', self.source)


if __name__ == "__main__":
    unittest.main()
