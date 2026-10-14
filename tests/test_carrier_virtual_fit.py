"""Prevent a plausible assembly pose from becoming a false fitment approval."""
import importlib.util
import hashlib
import json
from pathlib import Path
import unittest

from _deps import require_modules
require_modules('numpy')
import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/bionic-20261011/virtual_fit.py'
spec = importlib.util.spec_from_file_location('carrier_virtual_fit', SOURCE)
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)


class VirtualFitTests(unittest.TestCase):
    def test_retained_trial_keeps_sources_and_failure_status(self):
        root = SOURCE.parents[4]
        folder = root / 'parts/993-eng-carrier-0001/derived/virtual-fit-20261012'
        result = json.loads((folder / 'results.json').read_text())
        self.assertTrue(result['nominal_pattern_screen']['spacing_rejected'])
        self.assertFalse(result['source_geometry_modified'])
        self.assertFalse(result['fitment_validated'])
        self.assertFalse(result['manufacturing_authorized'])
        self.assertEqual(len(result['bolt_shank_interference_witnesses']), 4)
        self.assertTrue(all(x['samples_inside_bracket'] > 0 for x in result['bolt_shank_interference_witnesses']))
        for name, expected in result['inputs'].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        for name, expected in result['artifacts'].items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), expected, name)

    def test_existing_patterns_cannot_be_fixed_by_rigid_placement(self):
        carrier = [[-48, -23], [-48, 23], [48, -23], [48, 23]]
        bracket = [[-50, -20], [-50, 20], [50, -20], [50, 20]]
        result = fit.pattern_screen(carrier, bracket, 5.5, 5.25, 5)
        self.assertAlmostEqual(result['minimum_possible_max_axis_error_lower_bound_mm'], 3)
        self.assertEqual(result['combined_radial_bolt_clearance_mm'], .75)
        self.assertTrue(result['spacing_rejected'])

    def test_matching_rotated_reordered_pattern_cannot_grant_OEM_fit(self):
        a = np.array([[-48, -23], [-48, 23], [48, -23], [48, 23]])
        angle = .7
        r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        b = (a @ r.T + [87, -63])[[2, 0, 3, 1]]
        result = fit.pattern_screen(a, b, 5.5, 5.25, 5)
        self.assertFalse(result['spacing_rejected'])
        self.assertFalse(result['fitment_validated'])
        self.assertFalse(result['manufacturing_authorized'])

    def test_too_large_bolt_and_bad_geometry_are_rejected(self):
        a = [[-1, -1], [-1, 1], [1, -1], [1, 1]]
        self.assertTrue(fit.pattern_screen(a, a, 4, 10, 5)['spacing_rejected'])
        for invalid in (a[:3], [[0, 0]]*4, [[0, 0], [1, 0], [2, 0], [3, 0]],
                        [[float('nan'), 0], *a[1:]]):
            with self.assertRaises(ValueError):
                fit.pattern_screen(a, invalid, 5.5, 5.25, 5)
        with self.assertRaises(ValueError):
            fit.pattern_screen(a, a, 5.5, float('inf'), 5)
