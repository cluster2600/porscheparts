"""Boundary-contact screens must retain their documented false-negative scope."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
import audit_port_skin_openings as audit


class PortSkinOpeningTests(unittest.TestCase):
    def test_bbox_prefilter_retains_touching_boxes(self):
        first = [0., 0., 0., 1., 1., 1.]
        self.assertFalse(audit.disjoint_boxes(first, [1., 0., 0., 2., 1., 1.]))
        self.assertTrue(audit.disjoint_boxes(first, [1.01, 0., 0., 2., 1., 1.]))
        self.assertFalse(audit.disjoint_boxes(first, first))

    def test_native_healthy_and_hidden_pocket_counterexamples(self):
        if importlib.util.find_spec('OCP') is None:
            self.skipTest('OCP native witnesses require qualified CAD runtime')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            audit.self_test()
        result, ruled = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(result['native_witnesses'], 3)
        self.assertEqual(result['self_test'], 'PASS')
        self.assertTrue(result['inside_authorization_false_negative_demonstrated_and_raw_contacts_retained'])
        self.assertEqual(ruled['ruled_section_witness'], 'PASS')
        self.assertTrue(ruled['overshoot_free_vertex_section_bounds_checked'])


if __name__ == '__main__':
    unittest.main()
