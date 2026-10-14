"""Guard diagnostic field transfer against hidden peak loss and false approval."""
import importlib.util
import json
from pathlib import Path
import unittest

from _deps import require_modules
require_modules('numpy')
import numpy as np

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/bionic-20261011/native-leap71'
spec = importlib.util.spec_from_file_location('carrier_fields', SOURCE/'prepare.py')
fields = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fields)


class CarrierNativeFieldsTests(unittest.TestCase):
    def test_scalar_collision_retains_peak_including_negative_coordinates(self):
        rows, info = fields.sparse_bins([[-.11,0,0],[.12,0,0],[-1,0,0]], [[15],[100],[5]], .5)
        self.assertEqual(rows.tolist(), [[-1,0,0,5],[0,0,0,100]])
        self.assertEqual(info['discarded_colliding_samples'], 1)
        self.assertEqual(info['stored_peak_magnitude'], 100)

    def test_vector_keeps_one_direction_without_averaging_opposing_samples(self):
        rows, info = fields.sparse_bins([[0,0,0],[.1,0,0]], [[-3,4,0],[6,0,0]], .5)
        self.assertEqual(rows.tolist(), [[0,0,0,6,0,0]])
        self.assertEqual(info['stored_peak_magnitude'], 6)

    def test_bad_data_rejected(self):
        for xyz, values, pitch in [([],[],.5), ([[0,0,0]],[[float('nan')]],.5),
                                   ([[float('inf'),0,0]],[[2]],.5),
                                   ([[0,0,0]],[[2]],0), ([[0,0]],[[2]],.5),
                                   ([[0,0,0]],[[1,2]],.5),
                                   ([[1e300,0,0]],[[2]],.5)]:
            with self.assertRaises(ValueError): fields.sparse_bins(xyz, values, pitch)

    def test_retained_run_never_applies_V5_fields_to_changed_trial(self):
        results = json.loads((SOURCE/'results.json').read_text())
        native, audit = results['native'], results['audit']
        self.assertEqual(native['source_geometry_sha256'], fields.V5_STL_SHA256)
        self.assertEqual(native['vdb']['fields'], 7)
        self.assertGreater(native['vdb']['exact_scalar_samples'], 0)
        self.assertGreater(native['vdb']['exact_vector_samples'], 0)
        self.assertFalse(native['new_solver_executed'])
        self.assertFalse(native['candidate_strength_validated'])
        self.assertFalse(native['manufacturing_authorized'])
        self.assertFalse(audit['candidate_solver_executed'])
        self.assertFalse(audit['manufacturing_authorized'])
        self.assertFalse(results['transfer']['candidate_fields_valid'])
        self.assertTrue(audit['protected_surface_pass'])
        self.assertTrue(audit['six_primary_bore_probe_pass'])
        self.assertFalse(audit['raw_surface_pass'])
        self.assertFalse(audit['mass_screen_pass'])
        self.assertEqual(audit['status'], 'rejected_geometry_audit')

    def test_sources_and_preview_match_retained_receipt(self):
        results = json.loads((SOURCE/'results.json').read_text())
        for name, expected in results['source_sha256'].items():
            self.assertEqual(fields.sha(SOURCE/name), expected, name)
        preview = SOURCE.parents[2]/'media/native-leap71-20261012.png'
        self.assertEqual(fields.sha(preview), results['preview_sha256'])
