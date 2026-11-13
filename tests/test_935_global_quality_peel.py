"""Exercise both arithmetic implementations of the versioned quality contract."""
from fractions import Fraction
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

import numpy as np


class GlobalQualityPeelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = Path(__file__).resolve().parents[1]
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        modules = []
        for original, patch in [('audit_surface_peels_v2.py', 'global_quality_operator.diff'),
                                ('verify_surface_peels.py', 'global_quality_verifier.diff')]:
            base = repo/'docs/research/935-condition-directed-20261105/source'/original
            delta = repo/'docs/research/935-residual-surface-audit-20261107/source'/patch
            target = Path(cls.temporary.name)/original
            subprocess.run(['patch', '-s', '-o', str(target), str(base), str(delta)], check=True,
                           capture_output=True, text=True)
            spec = importlib.util.spec_from_file_location(original[:-3], target)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            modules.append(module)
        cls.operator, cls.verifier = modules

    def test_existing_geometry_and_topology_refusals_still_hold(self):
        self.assertTrue(all(self.operator.controls().values()))
        self.assertTrue(all(self.verifier.controls().values()))

    def test_local_minimum_can_decrease_above_existing_warning(self):
        points = np.array([[0., 0, 0], [1., 1, 2.**-44], [1., 0, 0], [0., 2, 0]])
        verdict, proof = self.operator.geometry(points, [2, 3], Fraction(512, 1 << 52))
        self.assertEqual(verdict, 'admitted_geometry')
        result = self.verifier.patch_proof(points, [2, 3], Fraction(512, 1 << 52))
        self.assertEqual(proof['deviation'], result[0])
        self.assertEqual(proof['removed_volume'], result[1])

    def test_new_warning_face_is_refused_by_both_paths(self):
        points = np.array([[0., 0, 0], [1e6, 1, 2.**-44], [1e6, 0, 0], [0., 2, 0]])
        bound = Fraction(512*10**6, 1 << 52)
        self.assertEqual(self.operator.geometry(points, [2, 3], bound)[0], 'new_warning_face')
        with self.assertRaises(AssertionError):
            self.verifier.patch_proof(points, [2, 3], bound)
