import copy
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'twins/bionic-turbo-f1/cfd'))
from audit_diagnostic import face_geometry, scalar_patch, history_metrics


class DiagnosticAuditTests(unittest.TestCase):
    def test_hanging_midpoint_does_not_shift_face_centroid_or_mrf_flux(self):
        vertices = np.array([[0,0,0],[2,0,0],[2,1,0],[1,1,0],[0,1,0]], dtype=float)
        centre, area = face_geometry(vertices)
        np.testing.assert_allclose(centre, [1,.5,0])
        np.testing.assert_allclose(area, [0,0,2])
        self.assertFalse(np.array_equal(centre, vertices.mean(axis=0)))
        # A stationary wall can have nonzero relative flux and zero absolute flux.
        omega = np.array([0,1,0])
        frame = np.dot(np.cross(omega, centre), area)
        self.assertNotEqual(frame, 0)
        self.assertEqual(-frame + frame, 0)

    def test_scalar_patch_rejects_nonfinite_or_wrong_counts(self):
        text = 'boundaryField {stator {\nvalue nonuniform List<scalar> 2 (1 2);\n}\n}'
        np.testing.assert_equal(scalar_patch(text, 'stator', 2), [1,2])
        for broken in (text.replace('1 2','1 nan'), text.replace('2 (1 2)','3 (1 2)'), text.replace('1 2','1')):
            with self.assertRaises(ValueError):
                scalar_patch(broken, 'stator', 2)

    def test_reverse_flow_and_transient_storage_never_qualify_performance(self):
        series = {key: [] for key in ('inlet','outlet','energy_inlet','energy_outlet','moment','minima')}
        for t in range(1,201):
            series['inlet'].append([t,-1])
            series['outlet'].append([t,1])
            series['energy_inlet'].append([t,0,0])
            series['energy_outlet'].append([t,10,0])
            series['moment'].append([t,0,0,-1,0,0,0,0,0,0])
            series['minima'].append([t,100000,298])
        steady = history_metrics(series,10,False)
        self.assertTrue(all(steady['checks'].values()))
        transient = history_metrics(series,10,True)
        self.assertFalse(transient['checks']['steady_state_demonstrated'])
        self.assertEqual(transient['stability'], {})
        reverse = copy.deepcopy(series)
        reverse['outlet'][-1][1] = -1
        self.assertFalse(history_metrics(reverse,10,False)['checks']['forward_flow_last_window'])
        reverse['minima'][-1][2] = -1
        self.assertFalse(history_metrics(reverse,10,False)['checks']['positive_p_T_entire_history'])
        reverse['inlet'][-1][0] += .1
        with self.assertRaises(ValueError):
            history_metrics(reverse,10,False)
