import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'twins/935-horizontal-cooling-system-f0/source'))
try:
    import numpy as np
    from audit_cut_coverage import audit
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Requires numpy')
class CutCoverageTests(unittest.TestCase):
    def setUp(self):
        self.contour = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
        self.segments = np.stack((self.contour, np.roll(self.contour, -1, axis=0)), axis=1)

    def test_complete_contour_accepts_reversed_segment_directions(self):
        result = audit(self.segments[:, ::-1], self.contour)
        self.assertTrue(result['all_observed_segments_retained'])
        self.assertEqual(result['contour_edges_not_in_observed_segments'], 0)

    def test_closed_contour_with_additional_open_arc_is_rejected(self):
        arc = np.array([[[2, 0, 0], [3, 0, 0]]], float)
        result = audit(np.concatenate((self.segments, arc)), self.contour)
        self.assertFalse(result['all_observed_segments_retained'])
        self.assertEqual(result['observed_segments_not_in_selected_contour'], 1)

    def test_duplicate_observed_edge_is_not_silently_discarded(self):
        result = audit(np.concatenate((self.segments, self.segments[:1])), self.contour)
        self.assertFalse(result['all_observed_segments_retained'])
        self.assertEqual(result['observed_segments_not_in_selected_contour'], 1)

    def test_added_gap_closure_is_reported(self):
        result = audit(self.segments[:-1], self.contour)
        self.assertTrue(result['all_observed_segments_retained'])
        self.assertEqual(result['contour_edges_not_in_observed_segments'], 1)

    def test_cli_rejects_omitted_arc_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            arc = np.array([[[2, 0, 0], [3, 0, 0]]], float)
            source = directory / 'cut.npz'
            output = directory / 'audit.json'
            np.savez(source, segments=np.concatenate((self.segments, arc)), contour=self.contour)
            script = ROOT / 'twins/935-horizontal-cooling-system-f0/source/audit_cut_coverage.py'
            run = subprocess.run([sys.executable, str(script), str(source), str(output)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(json.loads(output.read_text())['observed_segments_not_in_selected_contour'], 1)
            repeated = subprocess.run([sys.executable, str(script), str(source), str(output)],
                                      capture_output=True, text=True, check=False)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(json.loads(output.read_text())['observed_segments_not_in_selected_contour'], 1)

    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):
            audit(self.segments, [[float('nan'), 0, 0]] * 3)


if __name__ == '__main__':
    unittest.main()
